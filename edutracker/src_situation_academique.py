import pandas as pd
import os
import json
import numpy as np

CWD = os.getcwd()

def get_data():
    return pd.read_csv("data/fr-en-situation_academique_covid.csv", sep=";").sort_values(by="date")

def df_to_json(df):
    academies = list(df.academie.unique())
    academies_nombre_classes_fermees=[]

    dict_json = {'academies': academies}

    for academie in academies:
        
        df_academie = df[df.academie == academie]
        dict_academie = {}
        for col in df_academie.columns:
            if col not in ["academie"]:
                dict_academie[col] = df_academie[col].fillna(0).to_list()
        dict_json[academie] = dict_academie
        academies_nombre_classes_fermees += [df_academie.nombre_classes_fermees.values[-1]]

    argsort = np.argsort(-np.array(academies_nombre_classes_fermees))
    dict_json["academies_sort_by_nombre_classes_fermees"] = list(np.array(academies)[argsort])

    return dict_json

def export_json(data_json):
    with open('data/' + 'fr-en-situation_academique_covid.json', 'w', encoding='utf-8') as f:
        json.dump(data_json, f, ensure_ascii=False, indent=4)


def main():
    df = get_data()
    data_json = df_to_json(df)
    export_json(data_json)

if __name__ == "__main__":
    main()