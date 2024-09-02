import pandas as pd
import matplotlib.pyplot as plt
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', type=str)
    args = parser.parse_args()

    try :
        data = pd.read_csv(args.file_path)
    except Exception as e:
        print(f"Couldn't open file : {e}")
        return
    print(data.info())
    #je considère que si drop battery serial est vide, la meme batterie a ete reutilisée
    data['Drop Battery Serial'] = data['Drop Battery Serial'].fillna(data['Collect Battery Serial'])

    #data.to_csv("completer.csv", index=False)
    #sous-ensembles pour les données de dépôt et de collecte
    colonnes_drop = ['Drop Battery Serial', 'Drop Battery', 'Drop Time']
    colonnes_collect = ['Collect Battery Serial', 'Collect Battery', 'Collect Time']
    drop_data = data[colonnes_drop].copy()
    collect_data = data[colonnes_collect].copy()

    #conversion pour éviter des warnings
    drop_data.loc[:, 'Drop Battery Serial'] = drop_data['Drop Battery Serial'].astype(str)
    collect_data.loc[:, 'Collect Battery Serial'] = collect_data['Collect Battery Serial'].astype(str)

    #trier les données par numéro de série de batterie et par date
    drop_data = drop_data.sort_values(by=['Drop Battery Serial', 'Drop Time'])
    collect_data = collect_data.sort_values(by=['Collect Battery Serial', 'Collect Time'])

    battery_cycles = {}

    # Calculer les cycles pour chaque batterie
    for serial in data['Drop Battery Serial'].unique():
        # Filtrer les données pour la batterie actuelle
        drop_battery_data = drop_data[drop_data['Drop Battery Serial'] == serial].reset_index(drop=True)
        collect_battery_data = collect_data[collect_data['Collect Battery Serial'] == serial].reset_index(drop=True)        
        total_cycles = 0.0
        used_collect_indices = set()
        
        #itérer sur les données de drop
        for i, drop_row in drop_battery_data.iterrows():
            drop_value = drop_row['Drop Battery']
            drop_time = drop_row['Drop Time']

            # prochaine valeur de collect pas deja utilisé
            next_collect = collect_battery_data[(collect_battery_data['Collect Time'] > drop_time) & (~collect_battery_data.index.isin(used_collect_indices))].head(1)
            
            if not next_collect.empty:
                collect_index = next_collect.index[0]
                collect_value = next_collect.iloc[0]['Collect Battery']

                # Calculer la décharge si une prochaine collecte est trouvée
                if pd.notnull(drop_value) and pd.notnull(collect_value):
                    discharge = drop_value - collect_value
                    total_cycles += discharge / 100.0
                    used_collect_indices.add(collect_index)
            elif pd.notnull(drop_value):
                # Si aucune collecte suivante n'est trouvée, ignorer cette drop value
                continue

        #
        for j, collect_row in collect_battery_data.iterrows():
            if j not in used_collect_indices:
                collect_time = collect_row['Collect Time']
                
                # Cas particulier, je considere que si la 1ere valeur en collect est la plus ancienne la batterie était charger a 100%
                if total_cycles == 0.0:
                    previous_drops = drop_battery_data[drop_battery_data['Drop Time'] < collect_time]
                    if previous_drops.empty:
                        collect_value = collect_row['Collect Battery']
                        total_cycles += (100 - collect_value) / 100.0
                        used_collect_indices.add(j)
        
        # Stocker le nombre de cycles pour cette batterie
        battery_cycles[serial] = total_cycles

    battery_cycles_summary = pd.DataFrame.from_dict(battery_cycles, orient='index', columns=['Cycles'])

#Fichier result
    with open("result.txt", "w") as f:
        for serial, cycles in battery_cycles.items():
            if cycles < 0:
                f.write(f"anomalie sur batterie {serial} : {cycles} cycles\n")
            else:
                f.write(f"Battery Serial: {serial} : {cycles} cycles\n")
    plt.figure(figsize=(14, 6))
# Histogramme
    plt.subplot(1, 2, 1)
    plt.hist(battery_cycles_summary['Cycles'], bins=20, color='blue', edgecolor='black')
    plt.title('Distribution des Cycles de Batterie')
    plt.xlabel('Nombre de Cycles')
    plt.ylabel('Fréquence')

#Scatter
    plt.subplot(1, 2, 2)
    plt.scatter(range(len(battery_cycles_summary)), battery_cycles_summary['Cycles'], color='red')
    plt.title('Nuage de Points des Cycles par Batterie')
    plt.xlabel('Batterie')
    plt.ylabel('Nombre de Cycles')
    plt.xticks([])

#affichage
    plt.tight_layout()
    plt.show()
    print("Calcul des cycles terminé et résultats sauvegardés dans 'result.txt'.")

if __name__ == "__main__":
    main()