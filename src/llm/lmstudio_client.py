from openai import OpenAI
import json
import logging
from typing import Dict, Optional
from config.settings import settings


class LMStudioClient:
    """Cliente para interactuar con LM Studio local"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = settings.lmstudio_base_url
        self.model = settings.lmstudio_model
        self.client = None
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Verifica si LM Studio está disponible"""
        self.logger.info("="*60)
        self.logger.info("🤖 VERIFICANDO CONEXIÓN CON LM STUDIO")
        self.logger.info(f"📍 URL: {self.base_url}")
        self.logger.info("="*60)
        
        try:
            # Crear cliente OpenAI apuntando a LM Studio
            self.logger.debug("Creando cliente OpenAI...")
            self.client = OpenAI(
                base_url=self.base_url,
                api_key="lm-studio",  # LM Studio no requiere API key real
                timeout=90.0  # Timeout de 90 segundos para procesamiento de IA
            )
            
            # Intentar listar modelos disponibles
            self.logger.info("📋 Consultando modelos disponibles...")
            models_response = self.client.models.list()
            available_models = [model.id for model in models_response.data]
            
            if not available_models:
                self.logger.warning("⚠️ No hay modelos cargados en LM Studio")
                self.logger.warning("💡 Abre LM Studio y carga un modelo en la pestaña 'Local Server'")
                return False
            
            self.logger.info(f"✅ Encontrados {len(available_models)} modelo(s):")
            for idx, model in enumerate(available_models, 1):
                self.logger.info(f"   {idx}. {model}")
            
            # Verificar si el modelo configurado está disponible
            if self.model not in available_models:
                # Usar el primer modelo disponible
                old_model = self.model
                self.model = available_models[0]
                self.logger.info(f"🔄 Modelo '{old_model}' no encontrado")
                self.logger.info(f"✅ Usando modelo: {self.model}")
            else:
                self.logger.info(f"✅ Usando modelo configurado: {self.model}")
            
            self.logger.info("="*60)
            self.logger.info("✅ LM STUDIO CONECTADO EXITOSAMENTE")
            self.logger.info("="*60)
            return True
            
        except ConnectionError as e:
            self.logger.error("="*60)
            self.logger.error("❌ ERROR DE CONEXIÓN")
            self.logger.error(f"No se puede conectar a LM Studio en {self.base_url}")
            self.logger.error("💡 Verifica que:")
            self.logger.error("   1. LM Studio está abierto")
            self.logger.error("   2. El servidor local está iniciado")
            self.logger.error("   3. El puerto 1234 está disponible")
            self.logger.error(f"Detalles: {e}")
            self.logger.error("="*60)
            return False
        except Exception as e:
            self.logger.error("="*60)
            self.logger.error("❌ LM STUDIO NO DISPONIBLE")
            self.logger.error(f"Error: {type(e).__name__}: {e}")
            self.logger.error("💡 Funcionará en modo fallback (reglas)")
            self.logger.error("="*60)
            return False
    
    def chat_completion(self, prompt: str, system_message: str = None, temperature: float = 0.1, max_tokens: int = 2000) -> Optional[str]:
        """Realiza una consulta a LM Studio"""
        if not self.available or not self.client:
            self.logger.warning("🚫 LM Studio no disponible, no se puede hacer la consulta")
            return None
        
        try:
            messages = []
            
            if system_message:
                messages.append({
                    'role': 'system',
                    'content': system_message
                })
            
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            self.logger.info("🤖 Enviando petición a LM Studio...")
            self.logger.debug(f"   Modelo: {self.model}")
            self.logger.debug(f"   Temperature: {temperature}")
            self.logger.debug(f"   Prompt length: {len(prompt)} caracteres")
            
            import time
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9,
                timeout=120.0  # Timeout específico de 2 minutos para completions
            )
            
            elapsed_time = time.time() - start_time
            response_content = response.choices[0].message.content
            
            self.logger.info(f"✅ Respuesta recibida en {elapsed_time:.2f}s")
            self.logger.debug(f"   Respuesta length: {len(response_content)} caracteres")
            self.logger.debug(f"   Tokens usados: {getattr(response.usage, 'total_tokens', 'N/A')}")
            
            return response_content
            
        except Exception as e:
            self.logger.error("="*60)
            self.logger.error("❌ ERROR EN CONSULTA A LM STUDIO")
            self.logger.error(f"Tipo: {type(e).__name__}")
            self.logger.error(f"Mensaje: {e}")
            self.logger.error("="*60)
            return None
    
    def extract_job_info(self, job_text: str) -> Optional[Dict]:
        """Extrae información de ofertas de trabajo usando LM Studio"""
        self.logger.info("📊 Extrayendo información de oferta con LM Studio...")
        
        system_message = """Eres un experto en análisis de ofertas de trabajo. Tu tarea es extraer información estructurada de ofertas de trabajo y devolver SOLO un JSON válido sin texto adicional.

El JSON debe tener esta estructura exacta:
{
    "title": "Título del puesto",
    "seniority": "Junior/Mid/Senior",
    "location": "Ubicación",
    "salary_range": "Rango salarial si se menciona",
    "must_have": ["lista", "de", "requisitos", "obligatorios"],
    "nice_to_have": ["lista", "de", "requisitos", "deseables"],
    "years_experience": "Años de experiencia requeridos",
    "education": "Educación requerida",
    "description": "Resumen de la descripción"
}

Instrucciones:
- Extrae TODOS los requisitos técnicos mencionados
- Distingue entre requisitos obligatorios (must_have) y deseables (nice_to_have)
- Si no se especifica algo, usa null
- Devuelve SOLO el JSON, sin explicaciones"""

        prompt = f"""Analiza esta oferta de trabajo y extrae la información estructurada:

{job_text}

Responde SOLO con el JSON estructurado:"""

        response = self.chat_completion(prompt, system_message, temperature=0.1)
        
        if response:
            try:
                # Limpiar la respuesta para extraer solo el JSON
                cleaned_response = response.strip()
                
                # Buscar el JSON en la respuesta
                json_start = cleaned_response.find('{')
                json_end = cleaned_response.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = cleaned_response[json_start:json_end]
                    result = json.loads(json_str)
                    self.logger.info("✅ JSON parseado correctamente")
                    self.logger.debug(f"   Título: {result.get('title', 'N/A')}")
                    self.logger.debug(f"   Must-have: {len(result.get('must_have', []))} items")
                    self.logger.debug(f"   Nice-to-have: {len(result.get('nice_to_have', []))} items")
                    return result
                else:
                    self.logger.error("❌ No se encontró JSON válido en la respuesta")
                    self.logger.debug(f"Respuesta: {response[:200]}...")
                
            except json.JSONDecodeError as e:
                self.logger.error("❌ Error parsing JSON de LM Studio")
                self.logger.error(f"   Error: {e}")
                self.logger.debug(f"   Respuesta: {response[:500]}...")
        else:
            self.logger.warning("⚠️ No se recibió respuesta de LM Studio")
        
        return None
    
    def get_available_models(self) -> list:
        """Obtiene la lista de modelos disponibles"""
        try:
            if not self.client:
                return []
            models_response = self.client.models.list()
            return [model.id for model in models_response.data]
        except:
            return []
    
    def is_model_available(self, model_name: str) -> bool:
        """Verifica si un modelo específico está disponible"""
        available_models = self.get_available_models()
        return model_name in available_models


# Instancia global del cliente LM Studio
lmstudio_client = LMStudioClient()
