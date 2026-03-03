from typing import Dict, List, Tuple, Optional
import re
from dataclasses import dataclass
from enum import Enum

class SignalType(Enum):
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"

@dataclass
class RealismSignal:
    type: SignalType
    description: str
    impact: int  # 1-10, donde 10 es muy negativo

class RealismScorer:
    def __init__(self):
        # Rangos salariales por seniority (en miles €)
        self.salary_ranges = {
            'junior': {'min': 18, 'max': 35},
            'mid': {'min': 30, 'max': 55},
            'senior': {'min': 45, 'max': 80},
            'lead': {'min': 60, 'max': 120}
        }
        
        # Años de experiencia esperados por seniority
        self.experience_ranges = {
            'junior': {'min': 0, 'max': 3},
            'mid': {'min': 2, 'max': 6},
            'senior': {'min': 5, 'max': 12},
            'lead': {'min': 8, 'max': 20}
        }
        
        # Tecnologías por categorías
        self.tech_categories = {
            'frontend': [
                'react', 'angular', 'vue', 'javascript', 'typescript', 'html', 'css'
            ],
            'backend': ['python', 'java', 'node', 'php', 'c#', 'go', 'ruby'],
            'database': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'
            ],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes'],
            'mobile': ['ios', 'android', 'react native', 'flutter', 'swift', 'kotlin']
        }
        # Penalización por no especificar salario (puntos que se restarán)
        self.missing_salary_penalty = 15
    
    def calculate_realism_score(self, job_data: Dict) -> Dict:
        """Calcula el score de realismo y genera señales"""
        signals = []
        base_score = 100
        
        # Análisis de coherencia años/seniority
        years_signals, years_penalty = self._analyze_years_seniority_coherence(
            job_data.get('years_experience'), 
            job_data.get('seniority')
        )
        signals.extend(years_signals)
        base_score -= years_penalty
        
        # Análisis del stack tecnológico
        must_have = job_data.get('must_have') or []
        nice_to_have = job_data.get('nice_to_have') or []
        
        # Asegurar que ambos son listas
        if not isinstance(must_have, list):
            must_have = []
        if not isinstance(nice_to_have, list):
            nice_to_have = []
            
        stack_signals, stack_penalty = self._analyze_tech_stack_realism(
            must_have + nice_to_have
        )
        signals.extend(stack_signals)
        base_score -= stack_penalty
        
    # Análisis de salario (si disponible).
    # Si no está, penalizamos y marcamos salary_score = 0
        salary_penalty = 0
        if job_data.get('salary_range'):
            salary_signals, salary_penalty = self._analyze_salary_coherence(
                job_data.get('salary_range'),
                job_data.get('seniority'),
                job_data.get('location')
            )
            signals.extend(salary_signals)
            base_score -= salary_penalty
        else:
            # Penalizar la ausencia de rango salarial: afecta el score total
            signals.append(RealismSignal(
                SignalType.WARNING,
                "No se especifica rango salarial",
                5
            ))
            salary_penalty = self.missing_salary_penalty
            base_score -= salary_penalty
        
        # Análisis de contradicciones
        contradiction_signals, contradiction_penalty = (
            self._analyze_contradictions(job_data)
        )
        signals.extend(contradiction_signals)
        base_score -= contradiction_penalty
        
        # Análisis de longitud de requisitos
        length_signals, length_penalty = (
            self._analyze_requirements_length(job_data)
        )
        signals.extend(length_signals)
        base_score -= length_penalty
        
        final_score = max(0, min(100, base_score))
        
        # Calcular scores por categoría de forma más precisa
        years_seniority_score = max(0, 100 - years_penalty)
        tech_stack_score = max(0, 100 - stack_penalty)
        # Si no hay salario, marcar explícitamente 0 (y ya restamos su penalización)
        if job_data.get('salary_range'):
            salary_score = max(0, 100 - salary_penalty)
        else:
            salary_score = 0
        consistency_score = max(0, 100 - contradiction_penalty)

        # Si no hay información de años/seniority, mostrar que no se puede evaluar
        if (
            not job_data.get('years_experience')
            and not job_data.get('seniority')
        ):
            years_seniority_score = None
        elif (
            not job_data.get('years_experience')
            or not job_data.get('seniority')
        ):
            # Si solo falta uno, el score ya refleja la penalización
            pass

        return {
            "realism_score": final_score,
            "signals": [
                {
                    "type": s.type.value,
                    "description": s.description,
                    "impact": s.impact,
                }
                for s in signals
            ],
            "reasoning": self._generate_reasoning(final_score, signals),
            "categories": {
                "years_seniority": years_seniority_score,
                "tech_stack": tech_stack_score,
                "salary": salary_score,
                "consistency": consistency_score
            }
        }
    
    def _analyze_years_seniority_coherence(
        self,
        years_str: Optional[str],
        seniority: Optional[str]
    ) -> Tuple[List[RealismSignal], int]:
        """Analiza coherencia entre años de experiencia y seniority"""
        signals = []
        penalty = 0
        
        # Si ambos son None, no podemos evaluar - penalty moderada
        if (not years_str or years_str is None) and (not seniority or seniority is None):
            signals.append(RealismSignal(
                SignalType.INFO,
                "No hay información de experiencia ni seniority para evaluar",
                2
            ))
            return signals, 15  # Penalty por falta de información
        
        # Si solo uno es None, penalty menor pero notable
        if not years_str or years_str is None:
            signals.append(RealismSignal(
                SignalType.WARNING,
                "No hay información específica de años de experiencia",
                3
            ))
            return signals, 10
            
        if not seniority or seniority is None:
            signals.append(RealismSignal(
                SignalType.WARNING,
                "No hay información de nivel de seniority",
                3
            ))
            return signals, 10
        
        # Extraer números de la cadena de años
        years_numbers = re.findall(r'\d+', str(years_str))
        if not years_numbers:
            signals.append(RealismSignal(
                SignalType.WARNING,
                "No se pudo extraer años de experiencia específicos",
                3
            ))
            return signals, 5
        
        years = int(years_numbers[0])
        seniority_lower = seniority.lower()
        
        if seniority_lower in self.experience_ranges:
            expected_range = self.experience_ranges[seniority_lower]
            
            if years < expected_range['min']:
                penalty = (expected_range['min'] - years) * 5
                signals.append(RealismSignal(
                    SignalType.ERROR,
                    f"Años de experiencia ({years}) muy bajos para {seniority} (esperado: {expected_range['min']}-{expected_range['max']})",
                    8
                ))
            elif years > expected_range['max']:
                penalty = (years - expected_range['max']) * 2
                signals.append(RealismSignal(
                    SignalType.WARNING,
                    f"Años de experiencia ({years}) muy altos para {seniority} (esperado: {expected_range['min']}-{expected_range['max']})",
                    5
                ))
        
        return signals, min(penalty, 40)
    
    def _analyze_tech_stack_realism(self, requirements: List[str]) -> Tuple[List[RealismSignal], int]:
        """Analiza el realismo del stack tecnológico"""
        signals = []
        penalty = 0
        
        # Si no hay requisitos técnicos especificados
        if not requirements or len(requirements) == 0:
            signals.append(RealismSignal(
                SignalType.WARNING,
                "No se especifican requisitos técnicos específicos",
                4
            ))
            return signals, 12  # Penalty por falta de información técnica
        
        # Contar tecnologías por categoría
        tech_counts = {category: 0 for category in self.tech_categories}
        total_techs = 0
        
        req_text = ' '.join(requirements).lower()
        
        for category, techs in self.tech_categories.items():
            for tech in techs:
                if tech in req_text:
                    tech_counts[category] += 1
                    total_techs += 1
        
        # Señales basadas en el número total de tecnologías
        if total_techs > 15:
            penalty += 25
            signals.append(RealismSignal(
                SignalType.ERROR,
                f"Stack tecnológico excesivo: {total_techs} tecnologías (recomendado: <10)",
                9
            ))
        elif total_techs > 10:
            penalty += 10
            signals.append(RealismSignal(
                SignalType.WARNING,
                f"Stack tecnológico amplio: {total_techs} tecnologías",
                5
            ))
        
        # Señales por mezcla incompatible de tecnologías
        if tech_counts['frontend'] > 2 and tech_counts['backend'] > 2:
            penalty += 15
            signals.append(RealismSignal(
                SignalType.WARNING,
                "Se requieren múltiples frameworks frontend Y backend (fullstack muy amplio)",
                6
            ))
        
        if tech_counts['mobile'] > 1 and (tech_counts['frontend'] > 1 or tech_counts['backend'] > 1):
            penalty += 10
            signals.append(RealismSignal(
                SignalType.WARNING,
                "Se mezclan tecnologías móviles con web de forma excesiva",
                5
            ))
        
        return signals, min(penalty, 35)
    
    def _analyze_salary_coherence(
        self,
        salary_range: Optional[str],
        seniority: Optional[str],
        location: Optional[str]
    ) -> Tuple[List[RealismSignal], int]:
        """Analiza coherencia del salario"""
        signals = []
        penalty = 0
        
        if not salary_range or not seniority:
            return signals, penalty
        
        # Extraer números del rango salarial
        salary_numbers = re.findall(r'\d+', salary_range)
        if not salary_numbers:
            return signals, penalty
        
        salary = int(salary_numbers[0])
        if len(salary_numbers) > 1:
            salary = (int(salary_numbers[0]) + int(salary_numbers[-1])) // 2
        
        # Convertir a miles si es necesario
        if salary > 1000:
            salary = salary // 1000
        
        if seniority and seniority.lower() in self.salary_ranges:
            expected_range = self.salary_ranges[seniority.lower()]
            
            if salary < expected_range['min'] * 0.7:
                penalty += 20
                signals.append(RealismSignal(
                    SignalType.ERROR,
                    f"Salario ({salary}k) muy bajo para {seniority} (esperado: {expected_range['min']}-{expected_range['max']}k)",
                    7
                ))
            elif salary > expected_range['max'] * 1.5:
                penalty += 15
                signals.append(RealismSignal(
                    SignalType.WARNING,
                    f"Salario ({salary}k) muy alto para {seniority} (esperado: {expected_range['min']}-{expected_range['max']}k)",
                    6
                ))
        
        return signals, min(penalty, 25)
    
    def _analyze_contradictions(self, job_data: Dict) -> Tuple[List[RealismSignal], int]:
        """Busca contradicciones en la oferta"""
        signals = []
        penalty = 0
        
        description = job_data.get('description') or ''
        description = description.lower()
        
        # Contradicciones de modalidad
        if 'remoto' in description and 'presencial' in description and 'híbrido' not in description:
            penalty += 10
            signals.append(RealismSignal(
                SignalType.WARNING,
                "Contradicción en modalidad: menciona tanto remoto como presencial",
                5
            ))
        
        # Contradicciones de experiencia
        if 'junior' in description and ('senior' in description or 'años' in description):
            years_in_desc = re.findall(r'(\d+)\s*años', description)
            if years_in_desc and int(years_in_desc[0]) > 3:
                penalty += 15
                signals.append(RealismSignal(
                    SignalType.ERROR,
                    f"Contradicción: menciona 'junior' pero requiere {years_in_desc[0]} años",
                    7
                ))
        
        return signals, min(penalty, 20)
    
    def _analyze_requirements_length(self, job_data: Dict) -> Tuple[List[RealismSignal], int]:
        """Analiza la longitud excesiva de requisitos"""
        signals = []
        penalty = 0
        
        must_have = job_data.get('must_have') or []
        nice_to_have = job_data.get('nice_to_have') or []
        
        # Asegurar que ambos son listas
        if not isinstance(must_have, list):
            must_have = []
        if not isinstance(nice_to_have, list):
            nice_to_have = []
        
        total_requirements = len(must_have) + len(nice_to_have)
        
        if total_requirements > 20:
            penalty += 20
            signals.append(RealismSignal(
                SignalType.ERROR,
                f"Lista de requisitos excesiva: {total_requirements} items (recomendado: <15)",
                8
            ))
        elif total_requirements > 15:
            penalty += 10
            signals.append(RealismSignal(
                SignalType.WARNING,
                f"Lista de requisitos amplia: {total_requirements} items",
                4
            ))
        
        if len(must_have) > 12:
            penalty += 15
            signals.append(RealismSignal(
                SignalType.ERROR,
                f"Demasiados requisitos obligatorios: {len(must_have)} (recomendado: <8)",
                7
            ))
        
        return signals, min(penalty, 25)
    
    def _generate_reasoning(self, score: int, signals: List[RealismSignal]) -> str:
        """Genera explicación del score"""
        if score >= 85:
            base = "La oferta parece muy realista y bien estructurada."
        elif score >= 70:
            base = "La oferta es generalmente realista con algunas áreas de mejora."
        elif score >= 50:
            base = "La oferta presenta varios problemas de realismo que pueden disuadir candidatos."
        else:
            base = "La oferta tiene serios problemas de realismo y expectativas poco realistas."
        
        if signals:
            high_impact = [s for s in signals if s.impact >= 7]
            if high_impact:
                base += f" Principales problemas: {', '.join([s.description for s in high_impact[:2]])}."
        
        return base