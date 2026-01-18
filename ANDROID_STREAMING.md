# Implementación Android con Streaming

## Configuración de Gradle

```kotlin
// build.gradle.kts (Module: app)
dependencies {
    // Retrofit + OkHttp
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    
    // ViewModel y Lifecycle
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
}
```

## Modelos de Datos

```kotlin
// Models.kt
data class LoginRequest(
    val email: String,
    val password: String
)

data class TokenResponse(
    val access_token: String,
    val token_type: String
)

data class ChatRequest(
    val message: String,
    val use_context: Boolean = true
)

data class ChatMessageResponse(
    val role: String,
    val content: String,
    val created_at: String
)

data class ChatHistoryResponse(
    val messages: List<ChatMessageResponse>,
    val total: Int
)
```

## Servicio de API

```kotlin
// ChatbotApiService.kt
import retrofit2.Response
import retrofit2.http.*

interface ChatbotApiService {
    @POST("auth/register")
    suspend fun register(@Body request: LoginRequest): Response<TokenResponse>
    
    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>
    
    @GET("chat/history")
    suspend fun getChatHistory(
        @Header("Authorization") token: String,
        @Query("limit") limit: Int = 50
    ): Response<ChatHistoryResponse>
    
    @DELETE("chat/history")
    suspend fun clearHistory(
        @Header("Authorization") token: String
    ): Response<Map<String, String>>
    
    // El streaming se hace directamente con OkHttp (ver abajo)
}
```

## Cliente Retrofit

```kotlin
// RetrofitClient.kt
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    // Cambiar según tu configuración:
    // Emulador: http://10.0.2.2:8000/
    // Dispositivo físico: http://TU_IP:8000/
    private const val BASE_URL = "http://10.0.2.2:8000/"
    
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }
    
    val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)  // Más tiempo para streaming
        .build()
    
    val api: ChatbotApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ChatbotApiService::class.java)
    }
}
```

## Servicio de Chat con Streaming

```kotlin
// ChatService.kt
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import com.google.gson.Gson

class ChatService {
    private val client = RetrofitClient.okHttpClient
    private val baseUrl = "http://10.0.2.2:8000"  // Ajustar según tu caso
    private val gson = Gson()
    
    /**
     * Envía un mensaje y recibe respuesta en streaming
     * Devuelve un Flow que emite chunks de texto a medida que llegan
     */
    fun sendMessageStream(
        token: String,
        message: String,
        useContext: Boolean = true
    ): Flow<String> = flow {
        withContext(Dispatchers.IO) {
            val chatRequest = ChatRequest(message, useContext)
            val jsonBody = gson.toJson(chatRequest)
            
            val request = Request.Builder()
                .url("$baseUrl/chat/stream")
                .header("Authorization", "Bearer $token")
                .header("Content-Type", "application/json")
                .post(jsonBody.toRequestBody("application/json".toMediaType()))
                .build()
            
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    throw Exception("Error: ${response.code} - ${response.message}")
                }
                
                val source = response.body?.source() ?: throw Exception("No response body")
                
                while (!source.exhausted()) {
                    val line = source.readUtf8Line() ?: continue
                    
                    if (line.startsWith("data: ")) {
                        val data = line.removePrefix("data: ")
                        
                        if (data == "[DONE]") {
                            break
                        }
                        
                        // Emitir cada chunk
                        emit(data)
                    }
                }
            }
        }
    }
}
```

## ViewModel

```kotlin
// ChatViewModel.kt
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch

data class ChatUiState(
    val messages: List<ChatMessageResponse> = emptyList(),
    val currentResponse: String = "",
    val isLoading: Boolean = false,
    val error: String? = null
)

class ChatViewModel : ViewModel() {
    private val chatService = ChatService()
    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState
    
    fun sendMessage(token: String, message: String) {
        viewModelScope.launch {
            // Agregar mensaje del usuario
            val userMessage = ChatMessageResponse("user", message, "")
            _uiState.value = _uiState.value.copy(
                messages = _uiState.value.messages + userMessage,
                currentResponse = "",
                isLoading = true,
                error = null
            )
            
            // Recibir respuesta en streaming
            chatService.sendMessageStream(token, message)
                .catch { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = e.message
                    )
                }
                .collect { chunk ->
                    // Acumular respuesta
                    val newResponse = _uiState.value.currentResponse + chunk
                    _uiState.value = _uiState.value.copy(
                        currentResponse = newResponse
                    )
                }
            
            // Al terminar, agregar respuesta completa del asistente
            if (_uiState.value.currentResponse.isNotEmpty()) {
                val assistantMessage = ChatMessageResponse(
                    "assistant",
                    _uiState.value.currentResponse,
                    ""
                )
                _uiState.value = _uiState.value.copy(
                    messages = _uiState.value.messages + assistantMessage,
                    currentResponse = "",
                    isLoading = false
                )
            }
        }
    }
    
    fun loadHistory(token: String) {
        viewModelScope.launch {
            try {
                val response = RetrofitClient.api.getChatHistory("Bearer $token")
                if (response.isSuccessful && response.body() != null) {
                    _uiState.value = _uiState.value.copy(
                        messages = response.body()!!.messages
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }
}
```

## Activity/Fragment

```kotlin
// ChatActivity.kt
import android.os.Bundle
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class ChatActivity : AppCompatActivity() {
    private val viewModel: ChatViewModel by viewModels()
    private lateinit var tokenManager: TokenManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_chat)
        
        tokenManager = TokenManager(this)
        val token = tokenManager.getToken() ?: run {
            // Redirigir a login
            return
        }
        
        // Cargar historial
        viewModel.loadHistory(token)
        
        // Observar cambios de UI
        lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                // Actualizar RecyclerView con mensajes
                messagesAdapter.submitList(state.messages)
                
                // Mostrar respuesta en progreso
                if (state.currentResponse.isNotEmpty()) {
                    tvStreamingResponse.text = state.currentResponse
                    tvStreamingResponse.visibility = View.VISIBLE
                } else {
                    tvStreamingResponse.visibility = View.GONE
                }
                
                // Mostrar/ocultar loading
                progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                
                // Mostrar errores
                state.error?.let {
                    Toast.makeText(this@ChatActivity, it, Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        // Botón enviar
        btnSend.setOnClickListener {
            val message = etMessage.text.toString()
            if (message.isNotBlank()) {
                viewModel.sendMessage(token, message)
                etMessage.text.clear()
            }
        }
    }
}
```

## Layout con RecyclerView (Ejemplo)

```xml
<!-- activity_chat.xml -->
<LinearLayout
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical">
    
    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/rvMessages"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"/>
    
    <!-- Respuesta en streaming -->
    <TextView
        android:id="@+id/tvStreamingResponse"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:background="#E8F5E9"
        android:padding="16dp"
        android:visibility="gone"/>
    
    <ProgressBar
        android:id="@+id/progressBar"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_gravity="center"
        android:visibility="gone"/>
    
    <!-- Input de mensaje -->
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:padding="8dp">
        
        <EditText
            android:id="@+id/etMessage"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:hint="Escribe tu mensaje..."/>
        
        <Button
            android:id="@+id/btnSend"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Enviar"/>
    </LinearLayout>
</LinearLayout>
```

## Probar Conexión

Antes de ejecutar la app, verifica que el backend esté accesible:

```bash
# En WSL, levanta el servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Desde Android (adb shell) o terminal de tu PC:
curl http://10.0.2.2:8000/
# Debe responder: {"status":"200","message":"Backend Chatbot IA activo 🚀"}
```

## Troubleshooting

### Error de conexión
- Verificar que el servidor esté en `0.0.0.0:8000`
- Emulador: usar `10.0.2.2:8000`
- Dispositivo físico: usar IP de WSL (obtener con `ip addr show eth0`)
- Agregar permisos en AndroidManifest.xml:
  ```xml
  <uses-permission android:name="android.permission.INTERNET" />
  <application android:usesCleartextTraffic="true" ...>
  ```

### Streaming no funciona
- Verificar timeout de OkHttp (mínimo 120 segundos)
- Verificar que el header `Content-Type: application/json` esté presente
- Revisar logs con `HttpLoggingInterceptor`

### Token inválido
- Los tokens expiran en 60 minutos
- Guardar timestamp del login y renovar automáticamente
