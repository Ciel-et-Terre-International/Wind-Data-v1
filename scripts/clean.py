import os
import glob

def clean_noaa_csv_files(data_dir="data"):
    count = 0
    for root, dirs, files in os.walk(data_dir):
        for filename in files:
            if filename.startswith("noaa_station1_") and filename.endswith(".csv") \
            or filename.startswith("noaa_station2_") and filename.endswith(".csv") \
            or filename.startswith("raw_noaa_station") and filename.endswith(".csv"):
                file_path = os.path.join(root, filename)
                try:
                    os.remove(file_path)
                    print(f"🗑️ Supprimé : {file_path}")
                    count += 1
                except Exception as e:
                    print(f"⚠️ Erreur suppression {file_path} : {e}")

    if count == 0:
        print("✅ Aucun fichier NOAA trouvé à supprimer.")
    else:
        print(f"✅ {count} fichier(s) NOAA supprimé(s).")

if __name__ == "__main__":
    clean_noaa_csv_files()
