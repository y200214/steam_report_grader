# src/steam_report_grader/utils/id_generator.py

def generate_student_id(index: int, prefix: str = "S") -> str:
    """
    1 -> S001, 12 -> S012 みたいな形式で ID を作る。
    """
    return f"{prefix}{index:03d}"
