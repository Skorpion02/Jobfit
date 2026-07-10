"""JobFit — código fuente del agente.

Sub-paquetes:
    scraper/    Extracción de ofertas (genérico + LinkedIn)
    extractor/  Parsers de CV (PDF/DOCX/TXT) y de oferta
    auditor/    Score de realismo de ofertas
    matcher/    Matching semántico (Sentence Transformers)
    generator/  Adaptador de CV, optimizador ATS, analizador completo
    llm/        Cliente LM Studio (OpenAI-compat)
    utils/      Helpers compartidos (URL safety, normalización, …)
"""
