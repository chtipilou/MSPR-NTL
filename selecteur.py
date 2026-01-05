import questionary
import subprocess
import sys
import os

def run_script(script_name):
    """Exécute le script python sélectionné."""
    if os.path.exists(script_name):
        print(f"\n--- Lancement de {script_name} ---\n")
        try:
            # Exécute le script et attend la fin de son exécution
            subprocess.run([sys.executable, script_name], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n[Erreur] Le script s'est arrêté avec une erreur : {e}")
        except Exception as e:
            print(f"\n[Erreur] Impossible d'exécuter le script : {e}")
    else:
        print(f"\n[Fichier introuvable] {script_name} n'existe pas dans le dossier courant.")
    
    input("\nAppuyez sur Entrée pour revenir au menu...")

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Création de l'interface de sélection
        choice = questionary.select(
            "Que souhaitez-vous faire ?",
            choices=[
                "Sauvegarde MySQL (backup_mysql.py)",
                "Diagnostic Infrastructure (diagnostique_infra.py)",
                "Audit Système (audit.py)",
                questionary.Separator(),
                "Quitter"
            ],
            style=questionary.Style([
                ('qmark', 'fg:#fac731 bold'),       # Couleur du point d'interrogation
                ('question', 'bold'),               # Style de la question
                ('pointer', 'fg:#673ab7 bold'),     # Couleur de la flèche
                ('highlighted', 'fg:#673ab7 bold'), # Couleur du texte sélectionné
                ('selected', 'fg:#cc5454'),         # Couleur une fois validé
            ])
        ).ask()

        if choice == "Sauvegarde MySQL (backup_mysql.py)":
            run_script("backup_mysql.py")
        elif choice == "Diagnostic Infrastructure (diagnostique_infra.py)":
            run_script("diagnostique_infra.py")
        elif choice == "Audit Système (audit.py)":
            run_script("audit.py")
        else:
            print("Au revoir !")
            break

if __name__ == "__main__":
    main()
