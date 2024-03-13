#!/bin/sh
python --version
python3 --version
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install gpt-code-assistant
pip freeze > gpt-code-assistant/requirements.txt
pip install -r gpt-code-assistant/requirements.txt
echo "Lege ein Projekt an, um alle Dateien zu indizieren."
echo "Dieser Schritt beinhaltet die Erstellung von Embeddings für jede Datei und deren Speicherung in einer lokalen Datenbank, genannt code_base"
echo "To index your code project, please name a gpt-code-assistant project and provide your existing code project's path in the following steps."
# Ask for user_input
read -p "Please name your project: " projectname
# get current working directories absolut path as $codebase_path
pwd >> codebase_path
echo "Current codebase path is $codebase_path"
read -p "Change codebase's path: " codebase_path
echo "Creating Project with GPT-Code-Assistant by running\ngpt-code-assistant create-project <projektname> <pfad-zum-codebase>"
gpt-code-assistant create-project projectname codebase_path
echo "GPT-Code-Assistant created projekt $projectname with codebase located in $code_base"
echo "- Ask GPT-Code-Assistant a question: gpt-code-assistant query $projectname "Your question here"
echo "- Ask about codebasis:\n  COMMAND: query\r\t gpt-code-assistant query $projectname "Please explain this codebasis?"
echo "- Ask about project:\n  COMMAND: query\r\t gpt-code-assistant query $projectname "Please explain the project $projectname" 
echo "- Generate Test for a file:\n  COMMAND: query\r\t gpt-code-assistant query $projektname "Please generate a Test for analytics.py"
# gpt-code-assistant query $projectname $user_query


- Projekt aktualisieren:
Wenn du dein Projekt neu indizieren und die Embeddings auf den neuesten Stand bringen möchtest:

gpt-code-assistant refresh-project <projektname>

- Projekt löschen:
Um ein Projekt und alle seine Daten (einschließlich Embeddings) zu löschen:

gpt-code-assistant delete-project <projektname>

- Modell auswählen:
Du kannst das Modell auswählen, das für deine Anfragen verwendet werden soll:

gpt-code-assistant select-model

Standardmäßig wird gpt-3.5-turbo-16k verwendet.
Das Tool ist privacy-freundlich: Code-Snippets werden nur übertragen, wenn eine Frage gestellt wird und das Sprachmodell relevante Code-Ausschnitte anfordert. Zukünftige Pläne umfassen die Unterstützung lokaler Modelle und die Fähigkeit zur Code-Generierung..
