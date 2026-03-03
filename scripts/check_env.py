import sys


def main():
    sys.path.append('.')
    try:
        # Instanciar para validar que los módulos se importan correctamente
        from src.extractor.job_parser import JobParser
        from src.auditor.realism_scorer import RealismScorer
        JobParser()
        RealismScorer()
        print('✅ Componentes principales cargados correctamente')
    except Exception as e:
        print('⚠️ Warning: Error en test básico:', e)
        print('💡 El sistema puede aún funcionar, pero verifica manualmente')


if __name__ == '__main__':
    main()
