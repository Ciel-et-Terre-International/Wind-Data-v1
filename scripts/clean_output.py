import os
import shutil

def clean_data_outputs(data_folder='data'):
    print(f"📦 Nettoyage des dossiers 'figures_and_tables' et 'report' dans {data_folder}/")
    
    if not os.path.exists(data_folder):
        print(f"❌ Le dossier {data_folder} n'existe pas.")
        return

    for site_dir in os.listdir(data_folder):
        site_path = os.path.join(data_folder, site_dir)
        if not os.path.isdir(site_path):
            continue

        for sub in ['figures_and_tables', 'report']:
            path = os.path.join(site_path, sub)
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    print(f"✅ Supprimé : {path}")
                except PermissionError:
                    print(f"❌ Accès refusé : {path} → fermez les fichiers ou programmes qui l'utilisent.")
                except Exception as e:
                    print(f"⚠️ Erreur en supprimant {path} : {e}")
            else:
                print(f"[⏩] Non trouvé : {path}")

    print("✅ Nettoyage terminé.")

if __name__ == "__main__":
    clean_data_outputs()
