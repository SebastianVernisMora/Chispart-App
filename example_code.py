"""
Código de ejemplo para probar la generación de tests
"""

def calculate_area(length: float, width: float) -> float:
    """Calcula el área de un rectángulo"""
    if length <= 0 or width <= 0:
        raise ValueError("Las dimensiones deben ser positivas")
    return length * width


def fibonacci(n: int) -> int:
    """Calcula el n-ésimo número de Fibonacci"""
    if n < 0:
        raise ValueError("n debe ser no negativo")
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)


class Calculator:
    """Calculadora simple"""
    
    def __init__(self):
        self.history = []
    
    def add(self, a: float, b: float) -> float:
        """Suma dos números"""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def divide(self, a: float, b: float) -> float:
        """Divide dos números"""
        if b == 0:
            raise ZeroDivisionError("No se puede dividir por cero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result
    
    def get_history(self) -> list:
        """Retorna el historial de operaciones"""
        return self.history.copy()
