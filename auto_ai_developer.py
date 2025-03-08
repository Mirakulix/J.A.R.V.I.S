#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import subprocess
import traceback
import datetime
import requests
import json
from pathlib import Path
import pytest

model_name = "huihui_ai/deepseek-r1-abliterated"  

def create_dummy_model():
    """
    Erstellt ein Dummy-Modell für den Fall, dass kein echtes Modell verfügbar ist.
    
    Returns:
        dict: Ein Dummy-Modellobjekt
    """
    print("Erstelle Dummy-Modell für grundlegende Funktionalität...")
    return {"name": "dummy_model", "type": "dummy"}

def change_model_name(new_name=None):
    """
    Ändert den Modellnamen oder zeigt verfügbare Modelloptionen an.
    
    Args:
        new_name (str, optional): Der neue Modellname. Wenn None, werden Vorschläge angezeigt.
    """
    global model_name
    
    available_models = [
        "huihui_ai/deepseek-r1-abliterated",
        "codellama",             
        "phi2",                  
        "llama2",                
        "mistral",               
        "codegemma",             
        "deepseek-coder",        
        "wizard-coder",          
        "starcoder",             
        "neural-chat",           
        "orca-mini"              
    ]
    
    if new_name:
        model_name = new_name
        print(f"Modellname geändert zu: {model_name}")
    else:
        print("\nVerfügbare Modelloptionen:")
        for i, model in enumerate(available_models, 1):
            print(f"{i}. {model}")
        
        try:
            choice = input("\nWählen Sie ein Modell (Nummer) oder geben Sie einen Modellnamen ein: ")
            if choice.isdigit() and 1 <= int(choice) <= len(available_models):
                model_name = available_models[int(choice) - 1]
            else:
                model_name = choice
            
            print(f"Modellname geändert zu: {model_name}")
        except Exception as e:
            print(f"Fehler bei der Modellauswahl: {str(e)}")
            print(f"Verwende Standardmodell: {model_name}")

def load_model():
    """
    Prüft, ob Ollama verfügbar ist und das ausgewählte Modell verwenden kann.
    
    Returns:
        dict: Ein Modellobjekt oder None bei Fehler
    """
    global model_name
    print(f"Prüfe Ollama-Verbindung für Modell: {model_name}...")
    
    try:
        response = requests.get("http://localhost:11434/api/tags")
        
        if response.status_code == 200:
            available_models = response.json().get("models", [])
            model_names = [model["name"] for model in available_models]
            
            print(f"Verfügbare Ollama-Modelle: {', '.join(model_names)}")
            
            if model_name in model_names:
                print(f"Modell {model_name} ist verfügbar und wird verwendet.")
                return {"name": model_name, "type": "ollama"}
            else:
                print(f"Modell {model_name} ist nicht in Ollama verfügbar.")
                
                print("\nOptionen:")
                print("1. Ein anderes Modell auswählen")
                print("2. Dieses Modell in Ollama herunterladen")
                print("3. Ohne Modell fortfahren")
                
                choice = input("Wählen Sie eine Option (1-3): ")
                
                if choice == "1":
                    change_model_name()
                    return load_model()  
                elif choice == "2":
                    print(f"Starte Download von {model_name} in Ollama...")
                    try:
                        pull_response = requests.post(
                            "http://localhost:11434/api/pull",
                            json={"name": model_name}
                        )
                        
                        if pull_response.status_code == 200:
                            print(f"Modell {model_name} erfolgreich heruntergeladen.")
                            return {"name": model_name, "type": "ollama"}
                        else:
                            print(f"Fehler beim Herunterladen des Modells: {pull_response.text}")
                            return create_dummy_model()
                    except Exception as e:
                        print(f"Fehler beim Herunterladen des Modells: {str(e)}")
                        return create_dummy_model()
                else:
                    print("Verwende Dummy-Modell für Entwicklungszwecke...")
                    return create_dummy_model()
        else:
            print(f"Fehler bei der Verbindung zur Ollama-API: {response.status_code}")
            print("Stellen Sie sicher, dass Ollama installiert ist und läuft.")
            print("Installationsanweisungen: https://github.com/ollama/ollama")
            
            use_dummy = input("Möchten Sie ohne Modell fortfahren? (j/n): ")
            if use_dummy.lower() in ['j', 'ja', 'y', 'yes']:
                return create_dummy_model()
            else:
                print("Beende Programm.")
                sys.exit(1)
                
    except requests.exceptions.ConnectionError:
        print("Konnte keine Verbindung zur Ollama-API herstellen.")
        print("Stellen Sie sicher, dass Ollama installiert ist und läuft.")
        print("Installationsanweisungen: https://github.com/ollama/ollama")
        
        use_dummy = input("Möchten Sie ohne Modell fortfahren? (j/n): ")
        if use_dummy.lower() in ['j', 'ja', 'y', 'yes']:
            return create_dummy_model()
        else:
            print("Beende Programm.")
            sys.exit(1)
    
    except Exception as e:
        print(f"Unerwarteter Fehler beim Verbinden mit Ollama: {str(e)}")
        
        use_dummy = input("Möchten Sie ohne Modell fortfahren? (j/n): ")
        if use_dummy.lower() in ['j', 'ja', 'y', 'yes']:
            return create_dummy_model()
        else:
            print("Beende Programm.")
            sys.exit(1)
    
@pytest.fixture
def test_file():
    return os.path.join("tests", "test_case.py")

def test_analyze_code(testing_dir):
    result = analyze_code(testing_dir)
    assert result is not None
    return result

class ChatBot:
    def __init__(self):
        self.model = load_model()
        self.current_dir = Path(os.getcwd())
        self.backup_files = {}  

    def analyze_code(self, current_dir=None):
        """
        Analysiert alle Python-Dateien im angegebenen Verzeichnis und Unterverzeichnissen 
        und gibt grundlegende Statistiken zurück.

        Args:
            current_dir (Path, optional): Das zu analysierende Arbeitsverzeichnis. 
            Standardmäßig wird das aktuelle Verzeichnis verwendet.

        Returns:
            Dict: Ein Dictionary mit den Analyseergebnissen.
        """
        if current_dir is None:
            current_dir = self.current_dir
        
        py_files = [
            file for file in list(self.current_dir.glob("**/*.py"))
            if file.name != "auto_ai_developer.py" 
            and not any(venv_dir in str(file) for venv_dir in ['venv', '.venv'])
        ]

        if not py_files:
            return {
                "status": "no_python_files",
                "message": f"No Python files found in {current_dir}"
            }
        
        total_lines = 0
        unique_imports = set()
        unique_classes = set()
        unique_functions = set()
        file_details = {}
        
        for file in py_files:
            try:
                filename = file.name
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    total_lines += len(lines)
                    file_imports = set()
                    file_classes = set()
                    file_functions = set()
                    
                    for line in lines:
                        if line.strip().startswith('import') or line.strip().startswith('from'):
                            unique_imports.add(line.strip())
                            file_imports.add(line.strip())
                    
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.startswith('class '):
                            class_name = stripped.split('class ')[1].split('(')[0].strip()
                            unique_classes.add(class_name)
                            file_classes.add(class_name)
                        elif stripped.startswith('def '):
                            func_name = stripped.split('def ')[1].split('(')[0].strip()
                            unique_functions.add(func_name)
                            file_functions.add(func_name)
                    
                    file_details[str(file)] = {
                        "lines": len(lines),
                        "imports": list(file_imports),
                        "classes": list(file_classes),
                        "functions": list(file_functions)
                    }
            except Exception as e:
                print(f"Error analyzing file {file}: {str(e)}")
        
        average_line_length = total_lines / len(py_files) if py_files else 0
        
        return {
            "total_files": len(py_files),
            "total_lines": total_lines,
            "average_lines_per_file": round(average_line_length, 2),
            "unique_imports": len(unique_imports),
            "unique_classes": len(unique_classes),
            "unique_functions": len(unique_functions),
            "file_details": file_details
        }

    def display_analysis_results(self, analysis):
        """
        Zeigt die Ergebnisse der Code-Analyse in einer übersichtlichen Form an.
        
        Args:
            analysis (dict): Die Ergebnisse der Code-Analyse
        """
        print("\n" + "="*50)
        print(" CODE-ANALYSE ERGEBNISSE ".center(50, "="))
        print("="*50)
        
        if analysis.get('status') == 'no_python_files':
            print("✖ Keine Python-Dateien gefunden.")
            return
        
        print(f"📊 Dateien:      {analysis.get('total_files', 0):4d}")
        print(f"📊 Codezeilen:   {analysis.get('total_lines', 0):4d}")
        print(f"📊 ∅ Zeilen/Datei: {analysis.get('average_lines_per_file', 0):.1f}")
        print(f"📊 Importe:      {analysis.get('unique_imports', 0):4d}")
        print(f"📊 Klassen:      {analysis.get('unique_classes', 0):4d}")
        print(f"📊 Funktionen:   {analysis.get('unique_functions', 0):4d}")
        
        if 'file_details' in analysis and len(analysis['file_details']) > 0:
            print("\n🔍 Top 5 größte Dateien:")
            sorted_files = sorted(
                analysis['file_details'].items(), 
                key=lambda x: x[1]['lines'], 
                reverse=True
            )[:5]
            
            for file_path, details in sorted_files:
                file_name = Path(file_path).name
                print(f"  • {file_name:20s}: {details['lines']:4d} Zeilen")
            
            files_with_classes = {
                file_path: details for file_path, details in analysis['file_details'].items()
                if len(details['classes']) > 0
            }
            
            if files_with_classes:
                print("\n🔍 Dateien mit den meisten Klassen:")
                sorted_class_files = sorted(
                    files_with_classes.items(), 
                    key=lambda x: len(x[1]['classes']), 
                    reverse=True
                )[:3]
                
                for file_path, details in sorted_class_files:
                    file_name = Path(file_path).name
                    print(f"  • {file_name:20s}: {len(details['classes']):2d} Klassen")
        
        print("="*50)

    def test(self):
        """
        Führt alle Tests im tests-Verzeichnis aus, wenn es existiert.
        
        Returns:
            Dict: Ein Dictionary mit den Testergebnissen.
        """
        test_dir = self.current_dir / "tests"
        
        if not test_dir.exists():
            print(f"Keine Tests gefunden: {test_dir} existiert nicht.")
            return {"status": "no_tests", "message": f"No tests directory found at {test_dir}"}
        
        try:
            result = subprocess.run(
                ["pytest", "-v", str(test_dir)], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": "All tests passed",
                    "output": result.stdout
                }
            else:
                return {
                    "status": "failure",
                    "message": "Some tests failed",
                    "output": result.stdout,
                    "error": result.stderr
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error running tests: {str(e)}",
                "traceback": traceback.format_exc()
            }

    def fix_errors(self):
        """
        Analysiert alle Python-Dateien und setup.py-Dateien auf Fehler und korrigiert sie automatisch
        mit Hilfe der Ollama AI.
        
        Returns:
            Dict: Ein Dictionary mit den Korrekturergebnissen
        """
        print("\n" + "="*50)
        print(" FEHLERSUCHE UND -KORREKTUR ".center(50, "="))
        print("="*50)
        
        py_files = [
            file for file in list(self.current_dir.glob("**/*.py"))
            if file.name != "auto_ai_developer.py" 
            and not any(venv_dir in str(file) for venv_dir in ['venv', '.venv'])
        ]
        print(f"Prüfe {len(py_files)} Dateien auf Fehler...")
        
        setup_files = list(self.current_dir.glob("**/setup.py"))
        target_files = list(set(py_files + setup_files))  
        
        if not target_files:
            print("Keine Python-Dateien oder setup.py für die Fehlerkorrektur gefunden.")
            return {"status": "no_files", "message": "No files found for error correction"}
        
        print(f"Prüfe {len(target_files)} Dateien auf Fehler...")
        
        fixed_files = []
        errors_found = []
        
        for file in target_files:
            print(f"\nÜberprüfe: {file.relative_to(self.current_dir)}")
            
            if file.name == "setup.py":
                result = subprocess.run(
                    [sys.executable, str(file), "--dry-run"], 
                    capture_output=True, 
                    text=True
                )
            else:
                result = subprocess.run(
                    [sys.executable, str(file)], 
                    capture_output=True, 
                    text=True
                )
            
            if result.returncode == 0:
                print(f"✓ Keine Fehler gefunden in {file.name}")
                continue
            
            error_output = result.stderr if result.stderr else result.stdout
            error_line = error_output.strip().split('\n')[-1] if error_output else "Unbekannter Fehler"
            print(f"✗ Fehler gefunden in {file.name}:")
            print(f"  {error_line}")
            
            errors_found.append({
                "file": str(file),
                "error": error_output
            })
            
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                self.backup_files[str(file)] = file_content
                
                error_type, error_message, error_path, line_number = self.parse_error(error_output)
                
                if not all([error_type, error_message]) and file.name == "setup.py":
                    error_type = "SetupError"
                    error_message = error_line
                    line_number = 1  
                
                fixed_content = self.generate_ai_fix(
                    file_content,
                    error_type or "UnknownError",
                    error_message or error_line,
                    line_number or 1,
                    str(file)
                )
                
                if fixed_content != file_content:
                    print("\n  AI-generierte Korrektur:")
                    from difflib import unified_diff
                    diff = unified_diff(
                        file_content.splitlines(), 
                        fixed_content.splitlines(),
                        lineterm=''
                    )
                    for line in list(diff)[:10]:  
                        print(f"  {line}")
                    
                    with open(file, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    
                    print(f"  ✓ Änderungen automatisch angewendet in {file.name}")
                    fixed_files.append(str(file))
                    
                    print("  → Teste, ob der Fehler behoben wurde...")
                    if file.name == "setup.py":
                        verify_result = subprocess.run(
                            [sys.executable, str(file), "--dry-run"], 
                            capture_output=True, 
                            text=True
                        )
                    else:
                        verify_result = subprocess.run(
                            [sys.executable, str(file)], 
                            capture_output=True, 
                            text=True
                        )
                        
                    if verify_result.returncode == 0:
                        print(f"  ✓ Fehler in {file.name} wurde erfolgreich behoben!")
                    else:
                        print(f"  ✗ Fehler in {file.name} besteht weiterhin. Weiterer Korrekturversuch erforderlich.")
                        print(f"    Neue Fehlermeldung: {verify_result.stderr.strip().split('\n')[-1] if verify_result.stderr else 'Unbekannt'}")
                else:
                    print("  → Keine Änderungen von der AI vorgeschlagen.")
                
            except Exception as e:
                print(f"  ✗ Fehler bei der Bearbeitung: {str(e)}")
        
        print("\n" + "="*50)
        if fixed_files:
            print(f"✓ {len(fixed_files)} Dateien korrigiert.")
        else:
            print("Keine Dateien wurden korrigiert.")
        
        if len(errors_found) - len(fixed_files) > 0:
            print(f"✗ {len(errors_found) - len(fixed_files)} Dateien haben weiterhin Fehler.")
        
        print("="*50)
        
        return {
            "status": "completed",
            "errors_found": len(errors_found),
            "files_fixed": len(fixed_files),
            "fixed_files": fixed_files
        }

    def generate_ai_fix(self, content, error_type, error_message, line_number, file_path):
        """
        Verwendet das AI-Modell, um eine Fehlerkorrektur zu generieren.
        
        Args:
            content (str): Der Quellcode-Inhalt
            error_type (str): Der Fehlertyp (z.B. 'NameError')
            error_message (str): Die Fehlermeldung
            line_number (int): Die Zeilennummer des Fehlers
            file_path (str): Der Pfad zur Datei
            
        Returns:
            str: Der korrigierte Quellcode
        """
        if self.model.get("type") == "dummy":
            print("  → Keine AI-Unterstützung verfügbar im Dummy-Modus.")
            return content
        
        function_context = self.extract_function_context(content, line_number)
        
        prompt = f"""Fix Python error without any explanation. Return only the corrected code.

File: {file_path}
Error Type: {error_type}
Error Message: {error_message}

Current Code:
```python
{function_context if function_context else content}
```

Respond with the complete corrected code only, NO explanations. The response will be directly used to replace the code in the file.
"""
        
        print("  → Sende Fehler an Ollama zur Korrektur...")
        
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model.get("name"),
                    "prompt": prompt,
                    "system": "You are a precise Python code fixer. You respond only with correct code, no explanations.",
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  
                        "top_p": 0.95
                    }
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "")
                
                cleaned_response = self.extract_code_from_response(ai_response)
                
                if not cleaned_response or cleaned_response.strip() == content.strip():
                    print("  → AI konnte keine Verbesserungen vornehmen oder hat ungültigen Code zurückgegeben.")
                    return content
                
                return cleaned_response
            else:
                print(f"  ✗ Fehler bei der Ollama-API: {response.status_code} - {response.text}")
                return content
                
        except Exception as e:
            print(f"  ✗ Fehler bei der AI-Abfrage: {str(e)}")
            return content
    
    def extract_function_context(self, content, line_number):
        """
        Extrahiert den Kontext der Funktion, in der ein Fehler aufgetreten ist.
        
        Args:
            content (str): Der Quellcode-Inhalt
            line_number (int): Die Zeilennummer des Fehlers
            
        Returns:
            str: Der Funktionskontext oder None, wenn nicht gefunden
        """
        lines = content.split('\n')
        if line_number <= 0 or line_number > len(lines):
            return None
            
        start_line = line_number - 1
        indentation = None
        while start_line >= 0:
            current_line = lines[start_line]
            if not current_line.strip():
                start_line -= 1
                continue
                
            current_indent = len(current_line) - len(current_line.lstrip())
            
            if indentation is None:
                indentation = current_indent
            
            if (current_line.lstrip().startswith(('def ', 'class ')) and 
                current_indent < indentation):
                break
                
            if current_indent == 0 and current_line.strip() and not current_line.startswith('#'):
                break
                
            start_line -= 1
        
        end_line = line_number
        while end_line < len(lines):
            if end_line + 1 < len(lines):
                next_line = lines[end_line + 1].rstrip()
                if not next_line or (indentation is not None and 
                                     len(next_line) - len(next_line.lstrip()) <= indentation):
                    break
            end_line += 1
        
        return '\n'.join(lines[max(0, start_line):min(len(lines), end_line + 1)])
    
    def extract_code_from_response(self, response):
        """
        Extrahiert den Code aus der AI-Antwort.
        
        Args:
            response (str): Die Antwort der AI
            
        Returns:
            str: Extrahierter Code
        """
        code_block_pattern = r"```(?:python)?(.+?)```"
        code_blocks = re.findall(code_block_pattern, response, re.DOTALL)
        
        if code_blocks:
            return code_blocks[0].strip()
        
        lines = response.split('\n')
        code_lines = []
        for line in lines:
            if (line.strip() and 
                not line.strip().startswith('#') and 
                not line.startswith('Hier ist') and 
                not line.startswith('Here is') and
                not line.startswith('I fixed')):
                code_lines.append(line)
        
        return '\n'.join(code_lines)
    
    def parse_error(self, error_output):
        """
        Analysiert die Fehlerausgabe, um relevante Informationen zu extrahieren.
        Erweitert, um auch Fehler in setup.py und anderen Spezialsituationen zu erkennen.
        
        Args:
            error_output (str): Die Fehlerausgabe des Python-Interpreters
            
        Returns:
            Tuple: (error_type, error_message, file_path, line_number)
        """
        if not error_output:
            return None, None, None, None
            
        error_type = None
        error_message = None
        file_path = None
        line_number = None
        
        traceback_pattern = r'File "([^"]+)", line (\d+)'
        error_pattern = r'(\w+Error|Exception): (.+)'
        
        setup_error_pattern = r'error: (.+)'
        
        file_matches = re.findall(traceback_pattern, error_output)
        if file_matches:
            file_path, line_str = file_matches[-1]  
            try:
                line_number = int(line_str)
            except ValueError:
                line_number = 1
        
        error_matches = re.search(error_pattern, error_output)
        if error_matches:
            error_type = error_matches.group(1)
            error_message = error_matches.group(2)
        else:
            setup_matches = re.search(setup_error_pattern, error_output)
            if setup_matches:
                error_type = "SetupError"
                error_message = setup_matches.group(1)
            
            if not error_type and error_output.strip():
                error_type = "UnknownError"
                error_message = error_output.strip().split('\n')[-1]
        
        if not file_path and (error_type or error_message):
            file_path = "unknown_file.py"
            if not line_number:
                line_number = 1
        
        return error_type, error_message, file_path, line_number
    
    def fix_specific_error(self, content, error_type, error_message, line_number, file_path=None):
        """
        Behebt einen bestimmten Fehlertyp im Quellcode.
        
        Args:
            content (str): Der Quellcode-Inhalt
            error_type (str): Der Fehlertyp (z.B. 'NameError')
            error_message (str): Die Fehlermeldung
            line_number (int): Die Zeilennummer des Fehlers
            file_path (str, optional): Der Pfad zur Datei
            
        Returns:
            str: Der korrigierte Quellcode
        """
        lines = content.split('\n')
        fixed_content = content
        
        if error_type == 'NameError' and 'is not defined' in error_message:
            match = re.search(r"name '(\w+)' is not defined", error_message)
            if match:
                undefined_name = match.group(1)
                
                if undefined_name == 'pytest':
                    import_line = "import pytest"
                    if import_line not in content:
                        import_lines = [i for i, line in enumerate(lines) 
                                      if line.strip().startswith(('import ', 'from '))]
                        
                        if import_lines:
                            last_import = max(import_lines)
                            lines.insert(last_import + 1, import_line)
                        else:
                            lines.insert(0, import_line)
                        
                        fixed_content = '\n'.join(lines)
                        print(f"  → Füge Import hinzu: {import_line}")
        
        elif error_type == 'ImportError' and 'No module named' in error_message:
            match = re.search(r"No module named '(\w+)'", error_message)
            if match:
                missing_module = match.group(1)
                print(f"  → Fehlendes Modul: {missing_module}")
                print(f"  → Bitte installieren Sie das Modul mit: pip install {missing_module}")
        
        elif error_type == 'ImportError' and 'cannot import name' in error_message:
            match = re.search(r"cannot import name '(\w+)' from '([^']+)'", error_message)
            if match and file_path:
                missing_name = match.group(1)
                module_path = match.group(2)
                
                print(f"  → Fehlender Name: {missing_name} in Modul: {module_path}")
                
                module_parts = module_path.split('.')
                potential_file = os.path.join(self.current_dir, *module_parts) + '.py'
                potential_file = Path(potential_file)
                
                if potential_file.exists():
                    # Öffne die Moduldatei und füge die fehlende Funktion hinzu
                    with open(potential_file, 'r', encoding='utf-8') as f:
                        module_content = f.read()
                    
                    # Spezifische Funktionen basierend auf Namen und Modul
                    if missing_name == 'setup_routes' and 'api' in module_path and 'routes' in module_path:
                        # Beispiel für eine einfache setup_routes Funktion
                        new_content = module_content + '\n\n'
                        new_content += 'def setup_routes(app):\n'
                        new_content += '    """Setup API routes for the Flask app"""\n'
                        new_content += '    @app.route("/api/health", methods=["GET"])\n'
                        new_content += '    def health_check():\n'
                        new_content += '        """Health check endpoint"""\n'
                        new_content += '        from flask import jsonify\n'
                        new_content += '        return jsonify({"status": "ok"})\n'
                        
                        # Schreibe die Datei
                        with open(potential_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"  → Funktion {missing_name} wurde in {potential_file} hinzugefügt.")
                        return new_content
        
        # SyntaxError: Syntaxfehler
        elif error_type == 'SyntaxError':
            problem_line = lines[line_number - 1] if 0 <= line_number - 1 < len(lines) else ""
            print(f"  → Syntaxfehler in Zeile {line_number}: {problem_line}")
            
            # Einfache Syntaxfehler korrigieren
            if "EOL while scanning string literal" in error_message:
                # Ungeschlossene Anführungszeichen
                if "'" in problem_line and problem_line.count("'") % 2 == 1:
                    lines[line_number - 1] = problem_line + "'"
                    fixed_content = '\n'.join(lines)
                    print(f"  → Schließe fehlendes einfaches Anführungszeichen")
                elif '"' in problem_line and problem_line.count('"') % 2 == 1:
                    lines[line_number - 1] = problem_line + '"'
                    fixed_content = '\n'.join(lines)
                    print(f"  → Schließe fehlendes doppeltes Anführungszeichen")
            
            elif "unexpected EOF while parsing" in error_message:
                # Fehlende Klammer
                if problem_line.count('(') > problem_line.count(')'):
                    lines[line_number - 1] = problem_line + ')'
                    fixed_content = '\n'.join(lines)
                    print(f"  → Schließe fehlende Klammer")
                elif problem_line.count('{') > problem_line.count('}'):
                    lines[line_number - 1] = problem_line + '}'
                    fixed_content = '\n'.join(lines)
                    print(f"  → Schließe fehlende geschweifte Klammer")
                elif problem_line.count('[') > problem_line.count(']'):
                    lines[line_number - 1] = problem_line + ']'
                    fixed_content = '\n'.join(lines)
                    print(f"  → Schließe fehlende eckige Klammer")
            
        # Tokenizer Fehler bei der Generierung beheben
        elif 'handle_input' in content and 'generate' in error_message:
            for i, line in enumerate(lines):
                # Suche nach der handle_input-Methode, die einen Tokenizer-Fehler verursachen könnte
                if 'def handle_input' in line:
                    # Suche nach der problematischen Zeile in der Methode
                    method_lines = []
                    j = i + 1
                    while j < len(lines) and (lines[j].startswith(' ') or lines[j].strip() == ''):
                        method_lines.append(j)
                        j += 1
                    
                    # Korrigiere die generate-Methode
                    for j in method_lines:
                        if 'response = self.model.generate' in lines[j]:
                            # Ersetze mit korrekter API-Verwendung
                            old_line = lines[j]
                            lines[j] = (
                                '        response = requests.post(\n'
                                '            "http://localhost:11434/api/generate",\n'
                                '            json={\n'
                                '                "model": self.model.get("name"),\n'
                                '                "prompt": prompt,\n'
                                '                "stream": False\n'
                                '            }\n'
                                '        ).json().get("response", "Keine Antwort erhalten.")'
                            )
                            fixed_content = '\n'.join(lines)
                            print(f"  → Geändert: {old_line.strip()} -> API-basierte Generierung")
                            break
        
        return fixed_content

    def find_main_file(self):
        """
        Findet die Hauptdatei des Projekts (normalerweise die mit if __name__ == "__main__").
        
        Returns:
            str: Pfad zur Hauptdatei oder None, wenn nicht gefunden
        """
        py_files = [
            file for file in list(self.current_dir.glob("**/*.py"))
            if file.name != "auto_ai_developer.py" 
            and not any(venv_dir in str(file) for venv_dir in ['venv', '.venv'])
        ]
        
        for file in py_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'if __name__ == "__main__"' in content or "if __name__ == '__main__'" in content:
                        return str(file)
            except:
                continue
        
        return None

    def extract_requirements_from_markdown(self):
        """
        Extrahiert Anforderungen aus Markdown-Dateien (README.md, Dateien in project_docs/ und docs/)
        
        Returns:
            list: Liste von Anforderungen aus den Markdown-Dateien
        """
        requirements = []
        md_paths = [
            self.current_dir / "README.md",
            *list(self.current_dir.glob("project_docs/*.md")),
            *list(self.current_dir.glob("docs/*.md"))
        ]
        
        print("\n" + "="*50)
        print(" PROJEKTANFORDERUNGEN EXTRAHIEREN ".center(50, "="))
        print("="*50)
        
        for md_path in md_paths:
            if md_path.exists():
                try:
                    print(f"\nÜberprüfe Dokumentation: {md_path.relative_to(self.current_dir)}")
                    with open(md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extrahiere Anforderungen aus verschiedenen Markdown-Sektionen
                    headers = re.findall(r'##?\s+(.*?)\n', content)
                    req_sections = ['Anforderungen', 'Requirements', 'Features', 'Funktionalität', 'Functionality', 
                                    'User Stories', 'Aufgaben', 'Tasks', 'ToDo', 'To-Do', 'Backlog']
                    
                    for header in headers:
                        if any(req_word in header for req_word in req_sections):
                            print(f"  • Gefundene Anforderungssektion: '{header}'")
                            pattern = fr'##?\s+{re.escape(header)}\s*\n(.*?)(?=\n##|\Z)'
                            matches = re.search(pattern, content, re.DOTALL)
                            
                            if matches:
                                section_content = matches.group(1).strip()
                                
                                # Extrahiere Anforderungen aus Listen
                                list_items = re.findall(r'[-*]\s+(.*?)(?=\n[-*]|\n\n|\Z)', section_content, re.DOTALL)
                                
                                if list_items:
                                    for item in list_items:
                                        # Ignoriere leere oder zu kurze Items
                                        if item.strip() and len(item.strip()) > 5:
                                            requirements.append((header, item.strip()))
                                else:
                                    # Wenn keine Listen gefunden wurden, nutze ganze Sektion
                                    paragraphs = [p.strip() for p in section_content.split('\n\n') if p.strip()]
                                    for para in paragraphs:
                                        if len(para) > 5:
                                            requirements.append((header, para))
                
                    # Extrahiere Features oder Anforderungen aus Punktlisten unabhängig von Headers
                    list_items = re.findall(r'[-*]\s+(.*?)(?=\n[-*]|\n\n|\Z)', content, re.DOTALL)
                    for item in list_items:
                        item = item.strip()
                        # Filtere relevante Anforderungen mit Schlüsselwörtern
                        if item and len(item) > 5 and any(
                            keyword in item.lower() for keyword in 
                            ['implement', 'add', 'create', 'develop', 'enable', 'support', 
                             'allow', 'must', 'should', 'implement', 'hinzufügen', 'erstellen', 
                             'entwickeln', 'ermöglichen', 'unterstützen']):
                            if not any(item == req[1] for req in requirements):  # Verhindere Duplikate
                                requirements.append(('Punktliste', item))
                
                except Exception as e:
                    print(f"  ✗ Fehler beim Lesen oder Verarbeiten der Datei: {str(e)}")
        
        if requirements:
            print(f"\n✓ {len(requirements)} Anforderungen aus Dokumentation extrahiert:")
            for i, (section, req) in enumerate(requirements[:10], 1):  # Zeige nur die ersten 10
                print(f"  {i}. [{section}] {req[:100]}..." if len(req) > 100 else f"  {i}. [{section}] {req}")
            
            if len(requirements) > 10:
                print(f"  ... und {len(requirements) - 10} weitere")
        else:
            print("\n✗ Keine Anforderungen in den Markdown-Dateien gefunden.")
        
        print("="*50)
        return requirements

    def create_implementation_plan(self, requirements):
        """
        Erstellt einen Implementierungsplan auf Basis der extrahierten Anforderungen.
        
        Args:
            requirements (list): Liste von (Sektion, Anforderung) Tupeln
            
        Returns:
            list: Implementierungsplan mit strukturierten Aufgaben
        """
        if not requirements:
            return []
            
        print("\n" + "="*50)
        print(" IMPLEMENTIERUNGSPLAN ERSTELLEN ".center(50, "="))
        print("="*50)
        
        plan = []
        
        if self.model.get("type") == "dummy":
            print("  → Keine AI-Unterstützung verfügbar im Dummy-Modus.")
            # Einfacher Plan für Dummy-Modus
            for i, (section, req) in enumerate(requirements):
                plan.append({
                    "task_id": i + 1,
                    "section": section,
                    "requirement": req,
                    "description": f"Implementierung für: {req}",
                    "steps": ["Code identifizieren", "Anforderung implementieren", "Tests schreiben"],
                    "priority": "medium",
                    "implemented": False
                })
            return plan
            
        # Teile die Anforderungen in Gruppen auf, um den Kontext-Rahmen nicht zu sprengen
        batch_size = 5
        requirement_batches = [requirements[i:i + batch_size] for i in range(0, len(requirements), batch_size)]
        
        for batch_idx, req_batch in enumerate(requirement_batches):
            print(f"\nVerarbeite Anforderungs-Batch {batch_idx + 1}/{len(requirement_batches)}...")
            
            batch_text = "\n".join([f"{i+1}. [{section}] {req}" for i, (section, req) in enumerate(req_batch)])
            
            prompt = f"""Analysiere die folgenden Projektanforderungen und erstelle einen detaillierten Implementierungsplan:

{batch_text}

Für jede Anforderung, erstelle:
1. Eine präzise Beschreibung der zu implementierenden Funktionalität
2. Konkrete Implementierungsschritte
3. Priorität (high, medium, low)

Formatiere die Antwort als JSON-Array mit folgenden Feldern für jede Aufgabe:
{{
  "task_id": Nummer,
  "section": "Sektion aus dem Original",
  "requirement": "Originale Anforderung",
  "description": "Präzise Beschreibung",
  "steps": ["Schritt 1", "Schritt 2", ...],
  "priority": "high/medium/low",
  "implemented": false
}}

Antworte AUSSCHLIESSLICH mit dem JSON-Array, keine weiteren Erklärungen.
"""
            
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.model.get("name"),
                        "prompt": prompt,
                        "system": "Du bist ein Projektmanagement-Experte für Softwareprojekte.",
                        "stream": False,
                        "options": {
                            "temperature": 0.2
                        }
                    }
                )
                
                if response.status_code == 200:
                    ai_response = response.json().get("response", "")
                    
                    # Extrahiere JSON aus der Antwort
                    json_matches = re.search(r'(\[\s*\{.*\}\s*\])', ai_response, re.DOTALL)
                    if json_matches:
                        try:
                            batch_plan = json.loads(json_matches.group(1))
                            
                            # Füge global eindeutige IDs hinzu
                            offset = len(plan)
                            for i, task in enumerate(batch_plan):
                                task["task_id"] = i + 1 + offset
                            
                            plan.extend(batch_plan)
                            print(f"  ✓ {len(batch_plan)} Aufgaben zum Plan hinzugefügt")
                        except json.JSONDecodeError as e:
                            print(f"  ✗ Fehler beim Parsen des JSON: {str(e)}")
                            # Fallback: Einfache Tasks erstellen
                            for i, (section, req) in enumerate(req_batch):
                                task_id = i + 1 + len(plan)
                                plan.append({
                                    "task_id": task_id,
                                    "section": section,
                                    "requirement": req,
                                    "description": f"Implementierung für: {req}",
                                    "steps": ["Code analysieren", "Anforderung umsetzen", "Testen"],
                                    "priority": "medium",
                                    "implemented": False
                                })
                    else:
                        print("  ✗ Konnte kein JSON-Array in der AI-Antwort finden. Erstelle einfache Tasks...")
                        for i, (section, req) in enumerate(req_batch):
                            task_id = i + 1 + len(plan)
                            plan.append({
                                "task_id": task_id,
                                "section": section,
                                "requirement": req,
                                "description": f"Implementierung für: {req}",
                                "steps": ["Code analysieren", "Anforderung umsetzen", "Testen"],
                                "priority": "medium",
                                "implemented": False
                            })
                else:
                    print(f"  ✗ Fehler bei der Ollama-API: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"  ✗ Fehler bei der Plan-Erstellung: {str(e)}")
                
        # Sortiere Tasks nach Priorität (high -> medium -> low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        plan = sorted(plan, key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
        
        print(f"\n✓ Implementierungsplan mit {len(plan)} Aufgaben erstellt.")
        print("\nTop 5 Aufgaben nach Priorität:")
        for task in plan[:5]:
            print(f"  • [{task['priority'].upper()}] {task['description']}")
        
        print("="*50)
        return plan

    def implement_requirement(self, task):
        """
        Implementiert eine einzelne Anforderung aus dem Plan.
        
        Args:
            task (dict): Die zu implementierende Aufgabe
            
        Returns:
            bool: True, wenn die Implementierung erfolgreich war
        """
        print(f"\n--- Implementiere Aufgabe #{task['task_id']}: {task['description']} ---")
        
        # Analysiere Code, um relevante Dateien zu finden
        analysis = self.analyze_code()
        
        # Wenn kein Code existiert, kann die Anforderung nicht umgesetzt werden
        if analysis.get('status') == 'no_python_files':
            print("✗ Keine Python-Dateien gefunden. Kann Anforderung nicht implementieren.")
            return False
        
        # Identifiziere relevante Dateien basierend auf der Anforderung
        relevant_files = self.identify_relevant_files(task, analysis)
        
        if not relevant_files:
            print("✗ Keine relevanten Dateien für diese Anforderung gefunden.")
            return False
        
        # Implementiere die Anforderung in den relevanten Dateien
        success = False
        for file_path in relevant_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Erstelle Backup der Datei
                self.backup_files[str(file_path)] = file_content
                
                # Generiere den Code zur Implementierung der Anforderung
                print(f"Implementiere Anforderung in {file_path.name}...")
                implemented_code = self.generate_implementation(file_content, task, file_path)
                
                if implemented_code != file_content:
                    # Zeige die Änderungen an
                    print("Durchgeführte Änderungen:")
                    from difflib import unified_diff
                    diff = unified_diff(
                        file_content.splitlines(), 
                        implemented_code.splitlines(),
                        lineterm=''
                    )
                    for line in list(diff)[:10]:  # Zeige nur die ersten 10 Zeilen
                        print(f"  {line}")
                    
                    # Schreibe die Datei
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(implemented_code)
                    
                    print(f"✓ Anforderung in {file_path.name} implementiert")
                    success = True
                else:
                    print(f"⚠ Keine Änderungen an {file_path.name}")
            except Exception as e:
                print(f"✗ Fehler bei der Implementierung in {file_path.name}: {str(e)}")
        
        # Überprüfe, ob die Implementierung erfolgreich war
        if success:
            # Teste, ob die Änderungen Fehler verursachen
            check_result = self.test_implementation()
            if check_result["status"] == "success":
                print("✓ Implementierung erfolgreich und Tests bestanden")
                task["implemented"] = True
                return True
            else:
                print(f"⚠ Implementierung führte zu Fehlern: {check_result.get('message', '')}")
                # Versuche, die Fehler zu beheben
                fix_result = self.fix_errors()
                if fix_result.get('files_fixed', 0) > 0:
                    print("✓ Fehler automatisch behoben")
                    task["implemented"] = True
                    return True
                else:
                    print("✗ Fehler konnten nicht behoben werden")
                    # Stelle das Backup wieder her
                    for file_path, content in self.backup_files.items():
                        try:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            print(f"✓ Wiederherstellung der Datei {Path(file_path).name}")
                        except Exception as e:
                            print(f"✗ Fehler bei der Wiederherstellung von {Path(file_path).name}: {str(e)}")
                    return False
        else:
            print("✗ Keine Änderungen durchgeführt")
            return False

    def identify_relevant_files(self, task, analysis):
        """
        Identifiziert relevante Dateien für eine Anforderung.
        
        Args:
            task (dict): Die zu implementierende Aufgabe
            analysis (dict): Analyse-Ergebnisse
            
        Returns:
            list: Liste von relevanten Dateien (Path-Objekte)
        """
        if not analysis.get('file_details'):
            return []
        
        relevant_files = []
        
        # Extrahiere Keywords aus der Anforderung
        req_text = f"{task['section']} {task['requirement']} {task['description']}"
        keywords = re.findall(r'\b\w+\b', req_text.lower())
        important_keywords = []
        
        for keyword in keywords:
            # Ignoriere sehr kurze oder allgemeine Wörter
            if len(keyword) > 3 and keyword not in [
                'eine', 'einer', 'einem', 'einen', 'der', 'die', 'das', 'den', 'dem', 'ein',
                'und', 'oder', 'aber', 'denn', 'für', 'mit', 'von', 'ist', 'sind', 'werden',
                'the', 'that', 'this', 'these', 'those', 'will', 'have', 'been', 'was', 'were'
            ]:
                important_keywords.append(keyword)
        
        # Finde relevante Dateien basierend auf den Keywords
        file_scores = {}
        
        # Suche in Dateinamen und Inhalten nach den Keywords
        for file_path, details in analysis.get('file_details', {}).items():
            score = 0
            path_obj = Path(file_path)
            file_name = path_obj.name.lower()
            
            # Besonderes Gewicht für main.py, app.py, etc.
            if file_name in ['main.py', 'app.py', 'server.py', 'api.py']:
                score += 10
            
            # Gewichte Dateinamen höher
            for keyword in important_keywords:
                if keyword in file_name:
                    score += 5
            
            # Suche in Funktions- und Klassennamen
            for func in details.get('functions', []):
                for keyword in important_keywords:
                    if keyword in func.lower():
                        score += 3
            
            for cls in details.get('classes', []):
                for keyword in important_keywords:
                    if keyword in cls.lower():
                        score += 3
            
            # Wenn Inhalt nicht separat durchsucht werden kann, basiere Relevanz nur auf den bisherigen Scores
            file_scores[file_path] = score
        
        # Sortiere Dateien nach Relevanz und wähle die Top-N
        sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Wenn kein deutlicher Treffer, nimm die Hauptdatei oder alle Dateien mit Klassen
        if not sorted_files or sorted_files[0][1] == 0:
            main_file = self.find_main_file()
            if main_file:
                relevant_files.append(Path(main_file))
            
            # Füge Dateien mit Klassen hinzu, wenn weniger als 3 gefunden wurden
            if len(relevant_files) < 3:
                for file_path, details in analysis.get('file_details', {}).items():
                    if details.get('classes') and Path(file_path) not in relevant_files:
                        relevant_files.append(Path(file_path))
                        if len(relevant_files) >= 3:
                            break
        else:
            # Nehme die Top-3 Dateien
            for file_path, score in sorted_files[:3]:
                if score > 0:
                    relevant_files.append(Path(file_path))
        
        if not relevant_files:
            # Wenn immer noch keine Dateien gefunden wurden, wähle die ersten 3 Python-Dateien
            py_files = [
                file for file in list(self.current_dir.glob("**/*.py"))
                if file.name != "auto_ai_developer.py" 
                and not any(venv_dir in str(file) for venv_dir in ['venv', '.venv'])
            ]
            relevant_files = py_files[:3]
        
        print(f"Relevante Dateien für diese Anforderung:")
        for file in relevant_files:
            print(f"  • {file.relative_to(self.current_dir)}")
        
        return relevant_files

    def generate_implementation(self, content, task, file_path):
        """
        Generiert Code zur Implementierung einer Anforderung.
        
        Args:
            content (str): Der bestehende Quellcode
            task (dict): Die zu implementierende Aufgabe
            file_path (Path): Pfad zur Datei
            
        Returns:
            str: Der aktualisierte Quellcode
        """
        if self.model.get("type") == "dummy":
            print("  → Keine AI-Unterstützung verfügbar im Dummy-Modus.")
            return content
        
        steps_text = "\n".join([f"- {step}" for step in task.get('steps', [])])
        
        prompt = f"""Implementiere die folgende Anforderung ohne Erklärungen. Gib nur den verbesserten Code zurück.

Datei: {file_path.name}
Aufgabe: {task['description']}
Anforderungsdetails: {task['requirement']}
Implementierungsschritte:
{steps_text}

Aktueller Code:
```python
{content}
```

Integriere den Code für die neue Funktionalität nahtlos in den bestehenden Code:
1. Suche nach passenden Stellen für die Implementierung
2. Respektiere bestehendes Code-Design und -Stil
3. Füge Docstrings und Kommentare hinzu
4. Implementiere keine TO-DO Kommentare, sondern direkt den vollständigen Code

Rückgabe ist ausschließlich der vollständige aktualisierte Code ohne Erklärungen.
"""
        
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model.get("name"),
                    "prompt": prompt,
                    "system": "Du bist ein professioneller Python-Entwickler. Implementiere präzise und ordentlich.",
                    "stream": False,
                    "options": {
                        "temperature": 0.2
                    }
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "")
                
                # Extrahiere den Code aus der Antwort
                cleaned_response = self.extract_code_from_response(ai_response)
                
                if not cleaned_response or cleaned_response.strip() == content.strip():
                    print("  → KI konnte keine Verbesserungen vornehmen oder hat ungültigen Code zurückgegeben.")
                    return content
                
                return cleaned_response
            else:
                print(f"  ✗ Fehler bei der Ollama-API: {response.status_code} - {response.text}")
                return content
                
        except Exception as e:
            print(f"  ✗ Fehler bei der KI-Abfrage: {str(e)}")
            return content

    def test_implementation(self):
        """
        Testet die Implementierung, um sicherzustellen, dass sie keine Fehler verursacht.
        
        Returns:
            dict: Ergebnis der Tests
        """
        # Führe Tests aus, falls vorhanden
        test_result = self.test()
        
        # Wenn keine Tests vorhanden sind, führe die Hauptdatei aus
        if test_result.get('status') == 'no_tests':
            main_file = self.find_main_file()
            if main_file:
                try:
                    print(f"Führe Hauptdatei aus: {main_file}")
                    result = subprocess.run(
                        [sys.executable, main_file], 
                        capture_output=True, 
                        text=True
                    )
                    
                    if result.returncode == 0:
                        return {
                            "status": "success",
                            "message": "Hauptdatei erfolgreich ausgeführt",
                            "output": result.stdout
                        }
                    else:
                        return {
                            "status": "failure",
                            "message": "Fehler beim Ausführen der Hauptdatei",
                            "output": result.stdout,
                            "error":result.stderr
                        }
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Fehler beim Testen: {str(e)}",
                        "traceback": traceback.format_exc()
                    }
            
        return test_result

    def improve_iteratively(self):
        """
        Führt einen iterativen Prozess zur Verbesserung des Codes durch, basierend auf den Anforderungen
        in den Markdown-Dateien des Projekts. Erstellt eine ToDo-Liste und arbeitet diese schrittweise ab.
        """
        print("\n" + "="*50)
        print(" ANFORDERUNGSBASIERTE CODEOPTIMIERUNG ".center(50, "="))
        print("="*50)
        
        # 1. Extrahiere Anforderungen aus README.md und anderen Markdown-Dateien
        print("\n1. EXTRAHIERE ANFORDERUNGEN AUS PROJEKTDOKUMENTATION")
        requirements = self.extract_requirements_from_markdown()
        
        if not requirements:
            print("\n⚠️ Keine Anforderungen in den Projektdokumenten gefunden.")
            print("Suche nach syntaktischen Fehlern und allgemeinen Verbesserungen...")
            return self.fix_errors()
        
        # 2. Erstelle einen Implementierungsplan
        print("\n2. ERSTELLE ToDo-LISTE UND IMPLEMENTIERUNGSPLAN")
        implementation_plan = self.create_implementation_plan(requirements)
        
        if not implementation_plan:
            print("\n⚠️ Konnte keinen Implementierungsplan erstellen.")
            print("Führe stattdessen Standard-Codeoptimierung durch...")
            return self.fix_errors()
        
        # 3. Implementiere die Anforderungen iterativ
        print("\n3. IMPLEMENTIERE ANFORDERUNGEN")
        implemented_count = 0
        failed_count = 0
        
        # Wähle, wie viele Anforderungen maximal umgesetzt werden sollen
        max_implementations = min(len(implementation_plan), 50)  # Begrenze auf 5 Anforderungen pro Lauf
        
        for i, task in enumerate(implementation_plan[:max_implementations]):
            print(f"\n[{i+1}/{max_implementations}] ANFORDERUNG: {task['description']}")
            print(f"Priorität: {task['priority'].upper()}")
            print(f"Schritte: {', '.join(task['steps'])}")
            
            success = self.implement_requirement(task)
            
            if success:
                implemented_count += 1
                print(f"✓ Anforderung #{task['task_id']} erfolgreich implementiert")
            else:
                failed_count += 1
                print(f"✗ Implementierung von Anforderung #{task['task_id']} fehlgeschlagen")
        
        # 4. Führe Tests aus und behebe mögliche Fehler
        print("\n4. TESTE UND FINALISIERE IMPLEMENTIERUNGEN")
        test_results = self.test()
        
        if test_results.get('status') != 'success':
            print("\n⚠️ Tests schlagen fehl. Versuche, Fehler zu beheben...")
            fix_results = self.fix_errors()
            
            if fix_results.get('files_fixed', 0) > 0:
                print(f"✓ {fix_results.get('files_fixed')} Dateien wurden automatisch korrigiert")
            else:
                print("✗ Es konnten keine Fehler automatisch behoben werden")
        else:
            print("\n✓ Alle Tests erfolgreich")
        
        # 5. Zusammenfassung
        print("\n" + "="*50)
        print(" ANFORDERUNGSBASIERTE OPTIMIERUNG ABGESCHLOSSEN ".center(50, "="))
        print("="*50)
        print(f"✓ {implemented_count} Anforderungen erfolgreich implementiert")
        
        if failed_count > 0:
            print(f"✗ {failed_count} Anforderungen konnten nicht implementiert werden")
        
        # Zeige die nächsten Anforderungen aus dem Plan, die nicht umgesetzt wurden
        if len(implementation_plan) > max_implementations:
            print("\nNÄCHSTE ANFORDERUNGEN FÜR ZUKÜNFTIGE VERBESSERUNGEN:")
            for i, task in enumerate(implementation_plan[max_implementations:max_implementations+3]):
                print(f"  • [{task['priority'].upper()}] {task['description']}")
        
        print("="*50)
        
        return {
            "status": "completed",
            "requirements_total": len(requirements),
            "implemented": implemented_count,
            "failed": failed_count
        }

    def handle_input(self, prompt: str) -> str:
        """
        Verarbeitet Benutzereingaben und generiert eine Antwort mit dem Modell über Ollama API.
        Wenn einer der Befehle 'analyze', 'test', 'fix', 'improve', 'init' erkannt wird,
        werden die entsprechenden Methoden aufgerufen, statt die Eingabe an das Modell zu senden.
        
        Args:
            prompt (str): Die Benutzereingabe
            
        Returns:
            str: Die generierte Antwort oder Ergebnis der Methode
        """
        # Prüfe auf Befehle und führe die entsprechenden Methoden aus
        prompt_lower = prompt.lower().strip()
        
        # Kommandos abfangen und direkt an interne Methoden weiterleiten
        if prompt_lower == 'analyze':
            analysis = self.analyze_code()
            self.display_analysis_results(analysis)
            return "Analyse abgeschlossen."
        elif prompt_lower == 'test':
            test_results = self.test()
            if test_results.get('status') == 'no_tests':
                return "Keine Tests gefunden."
            elif test_results.get('status') == 'success':
                return "Alle Tests erfolgreich bestanden."
            else:
                return f"Einige Tests sind fehlgeschlagen: {test_results.get('message', '')}"
        elif prompt_lower == 'fix':
            fix_results = self.fix_errors()
            return f"Fehlerkorrektur abgeschlossen: {fix_results.get('files_fixed', 0)} Dateien korrigiert, {fix_results.get('errors_found', 0) - fix_results.get('files_fixed', 0)} Dateien haben weiterhin Fehler."
        elif prompt_lower == 'improve':
            self.improve_iteratively()
            return "Anforderungsbasierte Codeoptimierung abgeschlossen."
        elif prompt_lower == 'init':
            return "Bitte verwenden Sie den 'init' Befehl im Hauptmenü, nicht über die AI-Schnittstelle."
        
        # Wenn kein Befehl erkannt wurde, sende die Anfrage an das Modell
        # Prüfe, ob das Modell verfügbar ist
        if not hasattr(self, 'model'):
            return "Modell nicht verfügbar. Bitte neu initialisieren."
        
        # Wenn es ein Dummy-Modell ist, gib eine Standard-Antwort zurück
        if self.model.get("type") == "dummy":
            return "Dies ist eine Dummy-Antwort, da kein echtes Modell verfügbar ist."
        
        try:
            # Sende Anfrage an die Ollama API
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model.get("name"),
                    "prompt": prompt,
                    "system": "Du bist ein hilfreicher AI-Entwicklungsassistent, der Python-Code schreiben und analysieren kann.",
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                }
            )
            
            # Verarbeite die Antwort
            if response.status_code == 200:
                response_data = response.json()
                return response_data.get("response", "Keine Antwort erhalten.")
            else:
                error_msg = f"Fehler bei der Ollama-API: {response.status_code} - {response.text}"
                print(error_msg)
                return f"Konnte keine Antwort generieren. {error_msg}"
                
        except requests.exceptions.ConnectionError:
            return "Konnte keine Verbindung zur Ollama-API herstellen. Ist Ollama gestartet?"
            
        except Exception as e:
            error_msg = str(e)
            print(f"Fehler in handle_input: {error_msg}")
            return f"Ein unerwarteter Fehler ist aufgetreten: {error_msg}"

    def gather_project_info(self):
        """
        Fragt systematisch alle relevanten Informationen für ein neues Softwareprojekt ab.
        Basierend auf einer umfassenden Checkliste für Softwareprojekte.
        """
        project_info = {}
        
        print("\n" + "="*80)
        print("NEUES SOFTWAREPROJEKT INITIALISIEREN".center(80))
        print("="*80)
        print("\nEs wurden keine Python-Dateien im Projektverzeichnis gefunden.")
        print("Lassen Sie uns die grundlegenden Informationen für Ihr neues Softwareprojekt erfassen.\n")
        
        # Allgemeine Projektinformationen
        print("\n📋 ALLGEMEINE PROJEKTINFORMATIONEN")
        print("-" * 50)
        project_info["name"] = input("Projektname: ")
        project_info["goal"] = input("Was ist das Hauptziel des Projekts? ")
        project_info["stakeholders"] = input("Wer sind die Stakeholder und Endnutzer? ")
        project_info["existing_systems"] = input("Gibt es bestehende Systeme oder Abhängigkeiten? ")
        
        # Funktionale und nicht-funktionale Anforderungen
        print("\n📋 ANFORDERUNGEN")
        print("-" * 50)
        project_info["features"] = input("Welche Hauptfunktionen/Features soll das Projekt umfassen? ")
        project_info["nonfunctional"] = input("Gibt es besondere Anforderungen an Performance, Skalierbarkeit oder Sicherheit? ")
        project_info["ui_ux"] = input("Gibt es spezielle UI/UX-Anforderungen? ")
        
        # Technische Planung
        print("\n📋 TECHNISCHE PLANUNG")
        print("-" * 50)
        project_info["languages"] = input("Welche Programmiersprachen sollen verwendet werden? ")
        project_info["frameworks"] = input("Welche Frameworks und Bibliotheken sollen eingesetzt werden? ")
        project_info["database"] = input("Welche Datenbank(en) sollen verwendet werden? ")
        project_info["architecture"] = input("Welche Architektur wird angestrebt (Monolith, Microservices, etc.)? ")
        project_info["infrastructure"] = input("Welche Infrastruktur wird benötigt (Cloud, On-Premise, etc.)? ")
        
        # Projektmanagement
        print("\n📋 PROJEKTMANAGEMENT")
        print("-" * 50)
        project_info["methodology"] = input("Welche Entwicklungsmethodik soll verwendet werden (Scrum, Kanban, etc.)? ")
        project_info["timeline"] = input("Gibt es einen geplanten Zeitrahmen oder wichtige Deadlines? ")
        project_info["team"] = input("Wie ist das Entwicklungsteam zusammengesetzt? ")
        
        # Weitere wichtige Aspekte
        print("\n📋 WEITERE ASPEKTE")
        print("-" * 50)
        project_info["quality_testing"] = input("Gibt es spezielle Anforderungen an Tests und Codequalität? ")
        project_info["security"] = input("Welche Sicherheits- und Datenschutzanforderungen gibt es? ")
        project_info["documentation"] = input("Welche Art von Dokumentation wird benötigt? ")
        project_info["future"] = input("Gibt es geplante zukünftige Erweiterungen? ")
        
        # Zusammenfassung und Speicherung
        self.save_project_info(project_info)
        return project_info
        
    def save_project_info(self, project_info):
        """
        Speichert die gesammelten Projektinformationen in einer Datei.
        """
        project_dir = self.current_dir / "project_docs"
        project_dir.mkdir(exist_ok=True)
        
        # Projektdokumentation in Markdown erstellen
        doc_file = project_dir / "project_requirements.md"
        
        with open(doc_file, "w") as f:
            f.write(f"# {project_info['name']} - Projektdokumentation\n\n")
            f.write(f"## Projektübersicht\n\n")
            f.write(f"**Ziel:** {project_info['goal']}\n\n")
            f.write(f"**Stakeholder und Endnutzer:** {project_info['stakeholders']}\n\n")
            f.write(f"**Bestehende Systeme:** {project_info['existing_systems']}\n\n")
            
            f.write(f"## Anforderungen\n\n")
            f.write(f"### Funktionale Anforderungen\n\n")
            f.write(f"{project_info['features']}\n\n")
            f.write(f"### Nicht-funktionale Anforderungen\n\n")
            f.write(f"{project_info['nonfunctional']}\n\n")
            f.write(f"**UI/UX:** {project_info['ui_ux']}\n\n")
            
            f.write(f"## Technische Spezifikationen\n\n")
            f.write(f"**Programmiersprachen:** {project_info['languages']}\n\n")
            f.write(f"**Frameworks und Bibliotheken:** {project_info['frameworks']}\n\n")
            f.write(f"**Datenbank:** {project_info['database']}\n\n")
            f.write(f"**Architektur:** {project_info['architecture']}\n\n")
            f.write(f"**Infrastruktur:** {project_info['infrastructure']}\n\n")
            
            f.write(f"## Projektmanagement\n\n")
            f.write(f"**Methodik:** {project_info['methodology']}\n\n")
            f.write(f"**Zeitplan:** {project_info['timeline']}\n\n")
            f.write(f"**Team:** {project_info['team']}\n\n")
            
            f.write(f"## Weitere Aspekte\n\n")
            f.write(f"**Tests und Codequalität:** {project_info['quality_testing']}\n\n")
            f.write(f"**Sicherheit und Datenschutz:** {project_info['security']}\n\n")
            f.write(f"**Dokumentation:** {project_info['documentation']}\n\n")
            f.write(f"**Zukünftige Erweiterungen:** {project_info['future']}\n\n")
            
            f.write(f"\n\n_Erstellt am: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")
        
        # Zusätzlich eine Projektstruktur erstellen
        structure_file = project_dir / "project_structure.md"
        with open(structure_file, "w") as f:
            f.write(f"# {project_info['name']} - Empfohlene Projektstruktur\n\n")
            
            # Python-basierte Struktur als Beispiel
            if "python" in project_info['languages'].lower():
                f.write("```\n")
                f.write(f"{project_info['name'].lower().replace(' ', '_')}/\n")
                f.write("├── docs/               # Dokumentation\n")
                f.write("├── src/                # Quellcode\n")
                f.write("│   ├── __init__.py\n")
                f.write("│   ├── main.py         # Haupteinstiegspunkt\n")
                f.write("│   ├── config/         # Konfiguration\n")
                f.write("│   ├── core/           # Kernfunktionalität\n")
                f.write("│   ├── models/         # Datenmodelle\n")
                f.write("│   ├── utils/          # Hilfsfunktionen\n")
                f.write("│   └── api/            # API-Endpunkte (falls benötigt)\n")
                f.write("├── tests/              # Tests\n")
                f.write("│   ├── __init__.py\n")
                f.write("│   ├── test_main.py\n")
                f.write("│   └── ...\n")
                f.write("├── requirements.txt    # Abhängigkeiten\n")
                f.write("├── setup.py            # Installationsskript\n")
                f.write("├── README.md           # Projektbeschreibung\n")
                f.write("└── .gitignore          # Git-Ausnahmen\n")
                f.write("```\n\n")
            
            # Anpassung für Webprojekte
            if "web" in project_info['frameworks'].lower() or "javascript" in project_info['languages'].lower():
                f.write("### Alternative Struktur für Webprojekte\n\n")
                f.write("```\n")
                f.write(f"{project_info['name'].lower().replace(' ', '_')}/\n")
                f.write("├── frontend/           # Frontend-Code\n")
                f.write("│   ├── public/         # Statische Assets\n")
                f.write("│   ├── src/            # Quellcode\n")
                f.write("│   ├── package.json    # Abhängigkeiten\n")
                f.write("│   └── ...\n")
                f.write("├── backend/            # Backend-Code\n")
                f.write("│   ├── src/            # Quellcode\n")
                f.write("│   ├── tests/          # Tests\n")
                f.write("│   └── ...\n")
                f.write("├── docs/               # Dokumentation\n")
                f.write("└── README.md           # Projektbeschreibung\n")
                f.write("```\n")
        
        print(f"\nProjektinformationen wurden gespeichert in:\n- {doc_file}\n- {structure_file}")
        
        # Erstellen einer ersten Datei im src-Verzeichnis
        src_dir = self.current_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        if "python" in project_info['languages'].lower():
            main_file = src_dir / "main.py"
            with open(main_file, "w") as f:
                f.write(f'"""Main module for {project_info["name"]}"""\n\n')
                f.write('def main():\n')
                f.write(f'    """Main entry point for {project_info["name"]}"""\n')
                f.write('    print("Starting ' + project_info["name"] + '")\n\n')
                f.write('if __name__ == "__main__":\n')
                f.write('    main()\n')
            
            print(f"- Initiale Python-Datei erstellt: {main_file}")
        
        return doc_file

    def create_project_starter(self, project_info):
        """
        Erstellt eine grundlegende Projektstruktur basierend auf den gesammelten Informationen.
        """
        project_name = project_info['name'].lower().replace(' ', '_')
        
        # Verzeichnisstruktur erstellen
        directories = ["src", "tests", "docs"]
        
        # Erweiterte Struktur je nach Projekttyp
        if "python" in project_info['languages'].lower():
            directories.extend(["src/config", "src/core", "src/models", "src/utils"])
            if "api" in project_info['features'].lower():
                directories.append("src/api")
        
        for directory in directories:
            (self.current_dir / directory).mkdir(exist_ok=True, parents=True)
        
        print(f"\nGrundlegende Projektstruktur für '{project_info['name']}' erstellt.")
        print("Generiere nun die Projektdateien...")
        
        # Generiere alle benötigten Dateien
        created_files = self.generate_project_files(project_info)
        
        return created_files

    def generate_project_files(self, project_info):
        """
        Generiert systematisch alle relevanten Dateien für das Projekt.
        Führt nach jeder Dateierstellung eine Analyse durch.
        
        Args:
            project_info (dict): Die gesammelten Projektinformationen
            
        Returns:
            list: Liste der erstellten Dateien
        """
        created_files = []
        project_name = project_info['name'].lower().replace(' ', '_')
        is_python = "python" in project_info['languages'].lower()
        is_web = "web" in project_info['frameworks'].lower() or "javascript" in project_info['languages'].lower()
        
        print("\n" + "="*80)
        print("GENERIERE PROJEKTDATEIEN".center(80))
        print("="*80)
        
        # 1. README erstellen
        readme_file = self.current_dir / "README.md"
        print(f"\n📄 Erstelle README.md...")
        with open(readme_file, "w") as f:
            f.write(f"# {project_info['name']}\n\n")
            f.write(f"{project_info['goal']}\n\n")
            f.write("## Beschreibung\n\n")
            f.write(f"{project_info.get('features', 'Keine Beschreibung verfügbar.')}\n\n")
            f.write("## Installation\n\n")
            f.write("```bash\n")
            if is_python:
                f.write("# Virtuelle Umgebung erstellen und aktivieren\n")
                f.write("python -m venv venv\n")
                f.write("source venv/bin/activate  # Linux/Mac\n")
                f.write("# ODER\n")
                f.write("venv\\Scripts\\activate  # Windows\n\n")
                f.write("# Abhängigkeiten installieren\n")
                f.write("pip install -r requirements.txt\n")
            elif is_web:
                f.write("# Abhängigkeiten installieren\n")
                f.write("npm install\n")
            f.write("```\n\n")
            f.write("## Verwendung\n\n")
            f.write("```bash\n")
            if is_python:
                f.write(f"# Programm starten\n")
                f.write(f"python src/main.py\n")
            elif is_web:
                f.write("# Entwicklungsserver starten\n")
                f.write("npm run dev\n")
            f.write("```\n\n")
            f.write("## Features\n\n")
            features = project_info.get('features', '').split('.')
            for feature in features:
                if feature.strip():
                    f.write(f"- {feature.strip()}\n")
            f.write("\n## Lizenz\n\n")
            f.write("MIT\n")
        
        created_files.append(readme_file)
        
        # Python-spezifische Dateien
        if is_python:
            # Weitere Datei-Generierung für Python-Projekte würde hier stehen
            pass
            
        # Für jede erstellte Datei eine schnelle Analyse durchführen
        print("\n" + "="*80)
        print("ANALYSIERE ERSTELLTE DATEIEN".center(80))
        print("="*80)
        
        for file in created_files:
            if file.suffix == '.py':
                print(f"\nAnalysiere {file}...")
                try:
                    # Einfache Syntax-Prüfung
                    with open(file, 'r') as f:
                        content = f.read()
                    
                    # Führe Python-Syntax-Check durch
                    compile(content, file, 'exec')
                    print(f"✅ {file}: Keine Syntax-Fehler gefunden.")
                except SyntaxError as e:
                    print(f"❌ {file}: Syntax-Fehler gefunden - {str(e)}")
        
        print("\n" + "="*80)
        print("PROJEKTERSTELLUNG ABGESCHLOSSEN".center(80))
        print("="*80)
        
        return created_files

    def run_project_verification(self, created_files):
        """
        Führt einen Debug-, Test- und Korrekturlauf für das erstellte Projekt durch.
        
        Args:
            created_files (list): Liste der erstellten Projektdateien
            
        Returns:
            dict: Ergebnisse des Verifikationsprozesses
        """
        print("\n" + "="*80)
        print("PROJEKT-VERIFIZIERUNG STARTEN".center(80))
        print("="*80)
        
        # Finde die Hauptdatei (main.py) im Projekt
        main_files = []
        for file in created_files:
            if file.name == "main.py":
                main_files.append(file)
        
        if not main_files:
            print("❌ Keine main.py Datei gefunden. Verifikation nicht möglich.")
            return {"status": "error", "message": "No main file found"}
        
        main_file = main_files[0]  # Verwende die erste gefundene main.py
        
        print(f"\n1. Führe Hauptdatei aus: {main_file}")
        try:
            # Führe die Hauptdatei aus
            result = subprocess.run(
                [sys.executable, str(main_file)],
                capture_output=True,
                text=True,
                timeout=10  # Timeout nach 10 Sekunden
            )
            
            if result.returncode == 0:
                print(f"✅ Hauptdatei wurde erfolgreich ausgeführt.")
                print(f"Ausgabe:\n{result.stdout}")
            else:
                print(f"❌ Fehler beim Ausführen der Hauptdatei:")
                print(f"Fehlerausgabe:\n{result.stderr}")
                
                # Fehler beheben
                print("\nVersuche, Fehler zu beheben...")
                self.fix_errors()
        except subprocess.TimeoutExpired:
            print(f"⚠️ Zeitüberschreitung beim Ausführen der Hauptdatei.")
        except Exception as e:
            print(f"❌ Fehler: {str(e)}")
        
        # Weitere Verifikationsschritte könnten hier folgen
        
        print("\n" + "="*80)
        print("VERIFIKATION ABGESCHLOSSEN".center(80))
        print("="*80)
        
        return {"status": "completed"}

    def start(self):
        """
        Startet den Chatbot und erstellt den Hauptinteraktionsloop.
        """
        print("Starting the AI Developer Assistant...")
        print(f"Current working directory: {self.current_dir}")
        
        # Analyse beim Start ausführen
        analysis = self.analyze_code()
        
        # Wenn keine Python-Dateien gefunden wurden, starte den Projekterfassungsprozess
        if analysis.get('status') == 'no_python_files' or analysis.get('total_files', 0) == 0:
            print("\nKeine Python-Dateien im Projektverzeichnis gefunden.")
            start_new = input("Möchten Sie ein neues Softwareprojekt initialisieren? (j/n): ")
            
            if start_new.lower() in ['j', 'ja', 'y', 'yes']:
                # Sammle Projektinformationen
                project_info = self.gather_project_info()
                
                # Frage, ob eine grundlegende Projektstruktur erstellt werden soll
                create_structure = input("\nSoll eine grundlegende Projektstruktur erstellt werden? (j/n): ")
                
                if create_structure.lower() in ['j', 'ja', 'y', 'yes']:
                    # Erstelle Grundstruktur und generiere alle benötigten Dateien
                    created_files = self.create_project_starter(project_info)
                    
                    # Frage nach dem Debug-/Test-/Korrekturlauf
                    run_verification = input("\nMöchten Sie einen Debugging-, Test- und Korrekturlauf starten? (j/n/Enter=j): ")
                    
                    if not run_verification or run_verification.lower() in ['j', 'ja', 'y', 'yes', '']:
                        self.run_project_verification(created_files)
                    else:
                        print("Debug- und Testlauf übersprungen.")
                
                # Führe Analyse erneut aus, da wir jetzt Dateien erstellt haben
                analysis = self.analyze_code()
            else:
                print("Fortfahren ohne Projektinitialisierung.")
        
        # Zeige Codeanalyse an
        if analysis.get('status') != 'no_python_files' and analysis.get('total_files', 0) > 0:
            self.display_analysis_results(analysis)
        else:
            print("\nCode-Analyse: Keine Python-Dateien gefunden.")
        
        print("\n" + "="*50)
        print(" AI DEVELOPER ASSISTANT ".center(50, "="))
        print("="*50)
        
        # Befehlsübersicht
        commands = "Befehle: analyze, test, fix, improve, init, exit"
        
        while True:
            try:
                # Zeige die Befehlszeile vor jeder Eingabeaufforderung
                print(f"\n{commands}")
                user_input = input("\n>>> ")
                
                if user_input.lower() == 'exit':
                    print("Beende AI Developer Assistant.")
                    break
                elif user_input.lower() == 'analyze':
                    analysis = self.analyze_code()
                    self.display_analysis_results(analysis)
                elif user_input.lower() == 'test':
                    test_results = self.test()
                    if test_results.get('status') == 'no_tests':
                        print("✗ Keine Tests gefunden.")
                    elif test_results.get('status') == 'success':
                        print("✓ Alle Tests erfolgreich bestanden.")
                    else:
                        print("✗ Einige Tests sind fehlgeschlagen.")
                        print(test_results.get('output', ''))
                elif user_input.lower() == 'fix':
                    self.fix_errors()
                elif user_input.lower() == 'improve':
                    self.improve_iteratively()
                elif user_input.lower() == 'init':
                    project_info = self.gather_project_info()
                    create_structure = input("\nSoll eine grundlegende Projektstruktur erstellt werden? (j/n): ")
                    if create_structure.lower() in ['j', 'ja', 'y', 'yes']:
                        created_files = self.create_project_starter(project_info)
                        
                        # Frage nach dem Debug-/Test-/Korrekturlauf
                        run_verification = input("\nMöchten Sie einen Debugging-, Test- und Korrekturlauf starten? (j/n/Enter=j): ")
                        
                        if not run_verification or run_verification.lower() in ['j', 'ja', 'y', 'yes', '']:
                            self.run_project_verification(created_files)
                else:
                    # Verarbeite Benutzereingabe als Nachricht an das KI-Modell
                    bot_response = self.handle_input(user_input)
                    print(f"AI Assistant: {bot_response}")
            except Exception as e:
                print(f"Fehler aufgetreten: {str(e)}")
                traceback.print_exc()

# Hauptausführung
if __name__ == "__main__":
    print("Initializing AI Developer Assistant...")
    
    # Kommandozeilenargumente verarbeiten
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Developer Assistant")
    parser.add_argument("--no-model", action="store_true", help="Startet ohne ein Modell zu laden (Dummy-Modus)")
    parser.add_argument("--model", type=str, help="Spezifischer Ollama-Modellname zum Laden")
    parser.add_argument("--analyze-only", action="store_true", help="Führt nur eine Code-Analyse durch und beendet")
    parser.add_argument("--ollama-url", type=str, default="http://localhost:11434", 
                        help="URL der Ollama-API (Standard: http://localhost:11434)")
    args = parser.parse_args()
    
    try:
        # Modellnamen überschreiben, wenn angegeben
        if args.model:
            model_name = args.model
            print(f"Verwende angegebenes Modell: {model_name}")
        
        # Initialisiere Chatbot mit oder ohne Modell
        if args.no_model:
            # Erstelle einen Chatbot im Dummy-Modus ohne Modell
            class DummyChatBot(ChatBot):
                def __init__(self):
                    self.current_dir = Path(os.getcwd())
                    self.backup_files = {}
                    self.model = {"name": "dummy_model", "type": "dummy"}
            
            print("Starte im Dummy-Modus ohne Modell...")
            chatbot = DummyChatBot()
        else:
            chatbot = ChatBot()
        
        # Führe nur Analyse aus, wenn gewünscht
        if args.analyze_only:
            print("\nFühre Code-Analyse durch...")
            analysis = chatbot.analyze_code()
            print("\nCode-Analyse Ergebnisse:")
            for key, value in analysis.items():
                if key != "file_details":  # Detaillierte Dateiinformationen auslassen
                    print(f"- {key}: {value}")
            print("\nAnalyse abgeschlossen. Beende Programm.")
            sys.exit(0)
        
        # Starte den normalen Chatbot-Modus
        chatbot.start()
    except KeyboardInterrupt:
        print("\nProgramm vom Benutzer beendet.")
    except ImportError as ie:
        print(f"\nFehlende Abhängigkeit: {str(ie)}")
        print("Bitte installieren Sie die erforderlichen Pakete:")
        print("pip install requests pytest")
    except Exception as e:
        print(f"Kritischer Fehler: {str(e)}")
        traceback.print_exc()