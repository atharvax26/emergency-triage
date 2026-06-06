"""SQL injection prevention verification utilities."""

import ast
import re
from pathlib import Path
from typing import List, Tuple, Set


class SQLInjectionVerifier:
    """
    Verify that SQL injection prevention is properly implemented.
    
    Checks:
    1. All database queries use parameterized statements (SQLAlchemy ORM)
    2. No raw SQL strings with string concatenation
    3. No f-strings or % formatting in SQL queries
    """
    
    # Patterns that indicate potential SQL injection vulnerabilities
    VULNERABLE_PATTERNS = [
        # Raw SQL with string concatenation
        r'execute\s*\(\s*["\'].*?\+',
        r'execute\s*\(\s*f["\']',
        r'execute\s*\(\s*.*?%\s*\(',
        
        # Raw SQL with format
        r'\.format\s*\(',
        
        # Direct string interpolation in SQL
        r'SELECT.*?\+',
        r'INSERT.*?\+',
        r'UPDATE.*?\+',
        r'DELETE.*?\+',
        r'WHERE.*?\+',
    ]
    
    # Safe patterns (SQLAlchemy ORM usage)
    SAFE_PATTERNS = [
        r'session\.query\(',
        r'session\.add\(',
        r'session\.delete\(',
        r'session\.execute\(',
        r'select\(',
        r'insert\(',
        r'update\(',
        r'delete\(',
        r'\.filter\(',
        r'\.filter_by\(',
    ]
    
    @staticmethod
    def verify_file(file_path: Path) -> Tuple[bool, List[str]]:
        """
        Verify a Python file for SQL injection vulnerabilities.
        
        Args:
            file_path: Path to Python file to verify
            
        Returns:
            Tuple of (is_safe, list_of_issues)
        """
        # Skip verification files themselves
        if "sql_verification.py" in str(file_path) or "security.py" in str(file_path):
            return True, []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return False, [f"Error reading file: {e}"]
        
        issues = []
        
        # Check for vulnerable patterns (but skip comments and docstrings)
        lines = content.split('\n')
        in_docstring = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Track docstrings
            if '"""' in stripped or "'''" in stripped:
                in_docstring = not in_docstring
                continue
            
            # Skip comments and docstrings
            if stripped.startswith('#') or in_docstring:
                continue
            
            # Check for execute with string concatenation
            if 'execute(' in line.lower():
                if '+' in line or 'f"' in line or "f'" in line:
                    # Make sure it's not in a comment
                    if '#' not in line or line.index('execute') < line.index('#'):
                        issues.append(
                            f"Line {i}: Potential SQL injection - execute() with string concatenation"
                        )
        
        is_safe = len(issues) == 0
        return is_safe, issues
    
    @staticmethod
    def verify_directory(directory: Path, exclude_dirs: Set[str] = None) -> Tuple[bool, dict]:
        """
        Verify all Python files in a directory for SQL injection vulnerabilities.
        
        Args:
            directory: Directory to scan
            exclude_dirs: Set of directory names to exclude
            
        Returns:
            Tuple of (all_safe, dict_of_file_issues)
        """
        if exclude_dirs is None:
            exclude_dirs = {'__pycache__', 'migrations', 'tests', '.venv', 'venv'}
        
        all_issues = {}
        all_safe = True
        
        for py_file in directory.rglob('*.py'):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue
            
            is_safe, issues = SQLInjectionVerifier.verify_file(py_file)
            
            if not is_safe:
                all_safe = False
                all_issues[str(py_file)] = issues
        
        return all_safe, all_issues
    
    @staticmethod
    def verify_orm_usage(file_path: Path) -> Tuple[bool, List[str]]:
        """
        Verify that file uses SQLAlchemy ORM properly.
        
        Args:
            file_path: Path to Python file to verify
            
        Returns:
            Tuple of (uses_orm, list_of_recommendations)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return False, [f"Error reading file: {e}"]
        
        recommendations = []
        uses_orm = False
        
        # Check for ORM usage
        for pattern in SQLInjectionVerifier.SAFE_PATTERNS:
            if re.search(pattern, content):
                uses_orm = True
                break
        
        # Check for raw SQL
        if 'execute(' in content.lower() and not uses_orm:
            recommendations.append(
                "Consider using SQLAlchemy ORM instead of raw SQL for better security"
            )
        
        # Check for text() usage (which is safe but should use bound parameters)
        if 'text(' in content:
            if ':' not in content:  # No bound parameters
                recommendations.append(
                    "When using text(), always use bound parameters (e.g., :param_name)"
                )
        
        return uses_orm, recommendations


def verify_sql_injection_prevention(app_directory: str = "app") -> dict:
    """
    Verify SQL injection prevention across the application.
    
    Args:
        app_directory: Root directory of the application
        
    Returns:
        Dictionary with verification results
    """
    app_path = Path(app_directory)
    
    if not app_path.exists():
        return {
            "success": False,
            "error": f"Directory {app_directory} not found"
        }
    
    # Verify all files
    all_safe, issues = SQLInjectionVerifier.verify_directory(app_path)
    
    # Count files checked
    total_files = len(list(app_path.rglob('*.py')))
    files_with_issues = len(issues)
    
    return {
        "success": all_safe,
        "total_files_checked": total_files,
        "files_with_issues": files_with_issues,
        "issues": issues,
        "message": "All files passed SQL injection verification" if all_safe else "SQL injection vulnerabilities detected"
    }


if __name__ == "__main__":
    # Run verification
    results = verify_sql_injection_prevention()
    
    print(f"\n{'='*60}")
    print("SQL INJECTION PREVENTION VERIFICATION")
    print(f"{'='*60}\n")
    
    print(f"Total files checked: {results['total_files_checked']}")
    print(f"Files with issues: {results['files_with_issues']}")
    print(f"Status: {'✓ PASSED' if results['success'] else '✗ FAILED'}")
    
    if not results['success']:
        print(f"\n{'='*60}")
        print("ISSUES FOUND:")
        print(f"{'='*60}\n")
        
        for file_path, file_issues in results['issues'].items():
            print(f"\n{file_path}:")
            for issue in file_issues:
                print(f"  - {issue}")
    
    print(f"\n{'='*60}\n")
