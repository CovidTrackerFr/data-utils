#!/usr/bin/env python
# coding: utf-8

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly
from datetime import datetime
import os
import psutil
PATH = os.getcwd()


df_mortalite = pd.read_csv('https://www.insee.fr/fr/statistiques/fichier/4487988/2021-11-19_deces_quotidiens_departement_csv.zip', sep=";", encoding="'windows-1252'")
df_mortalite_2018 = pd.read_csv(PATH+'/covidtracker/input/deces_quotidiens_departement_csv_avec_2018.csv', sep=";", encoding="'windows-1252'")


df_mortalite_france = df_mortalite[df_mortalite["Zone"] == "France"]
df_mortalite_france_2018 = df_mortalite_2018[df_mortalite_2018["Zone"] == "France"]
window = 7
df_mortalite_france_2018.loc[:,"Total_deces_2018_diff"] = df_mortalite_france_2018["Total_deces_2018"].diff().rolling(window=window, center=True).mean()

df_mortalite_france.loc[:,"Total_deces_2019_diff"] = df_mortalite_france["Total_deces_2019"].diff().rolling(window=window, center=True).mean()
df_mortalite_france.loc[:,"Total_deces_2020_diff"] = df_mortalite_france["Total_deces_2020"].diff().rolling(window=window, center=True).mean()
df_mortalite_france.loc[:,"Total_deces_2021_diff"] = df_mortalite_france["Total_deces_2021"].diff().rolling(window=window, center=True).mean()


#### Construction du graphique
fig = make_subplots(specs=[[{"secondary_y": False}]])

# Ajout R_effectif estimé via les urgences au graph
"""fig.add_trace(go.Scatter(x = df_mortalite_france["Date_evenement"], y = df_mortalite_france["Total_deces_2018_diff"],
                    mode='lines',
                    line=dict(width=4, color="rgb(96, 178, 219)"),
                    name="Décès 2018",
                    marker_size=4,
                    showlegend=True
                       ))"""


fig.add_trace(go.Scatter(x = df_mortalite_france["Date_evenement"], y = df_mortalite_france["Total_deces_2019_diff"],
                    mode='lines',
                    line=dict(width=4, color="rgb(11, 131, 191)"),
                    name="Décès 2019",
                    marker_size=4,
                    showlegend=True
                       ))
fig.add_trace(go.Scatter(x = df_mortalite_france_2018["Date_evenement"], y = df_mortalite_france_2018["Total_deces_2018_diff"],
                    mode='lines',
                    line=dict(width=4, color="rgb(96, 178, 219)"),
                    name="Décès 2018",
                    marker_size=4,
                    showlegend=True
                       ))

fig.add_trace(go.Scatter(x = df_mortalite_france["Date_evenement"], y = df_mortalite_france["Total_deces_2020_diff"],
                    mode='lines',
                    line=dict(width=4, color="#ffa58f"),
                    name="Décès 2020",
                    marker_size=4,
                    showlegend=True
                       ))


fig.add_trace(go.Scatter(x = df_mortalite_france["Date_evenement"], y = df_mortalite_france["Total_deces_2021_diff"],
                    mode='lines',
                    line=dict(width=4, color="red"),
                    name="Décès 2021",
                    marker_size=4,
                    showlegend=True
                       ))

mortalite_now = df_mortalite_france.dropna()["Total_deces_2021_diff"].values[-1]
fig.add_trace(go.Scatter(x = [df_mortalite_france.dropna()["Date_evenement"].values[-1]], y = [mortalite_now],
                    mode='markers',
                    name="",
                    line=dict(width=4, color="red"),
                    marker_color='red',
                    marker_size=10,
                    showlegend=False
                            ))
# Modification du layout
fig.update_layout(
    margin=dict(
            l=0,
            r=0,
            b=50,
            t=70,
            pad=0
        ),
    legend_orientation="h",
    title={
                'text': "<b>Mortalité en France</b><br><sub>Moyenne mobile de {} jours pour lisser les irrégularités. Derniers jours non consolidés.".format(window),
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'},
    titlefont = dict(
                size=20),
    annotations = [
                dict(
                    x=0.5,
                    y=-0.1,
                    xref='paper',
                    yref='paper',
                    opacity=0.8,
                    text='Date : {}. Source : INSEE. Auteur : Guillaume Rozier - covidtracker.fr.'.format(datetime.now().strftime('%d %B %Y')),                    showarrow = False
                )]
                 )
fig.update_xaxes(title="", nticks=10)
fig.update_yaxes(title="", rangemode="tozero")

name_fig = "mortalite"
fig.write_image(PATH+"/covidtracker/output/{}.jpeg".format(name_fig), scale=3, width=900, height=550)

fig.update_layout(
    annotations = [
                dict(
                    x=0.5,
                    y=1.05,
                    xref='paper',
                    yref='paper',
                    xanchor='center',
                    text='Cliquez sur des éléments de légende pour les ajouter/supprimer',
                    showarrow = False
                )]
                 )
#plotly.offline.plot(fig, filename = PATH+'/covidtracker/output/{}.html'.format(name_fig), auto_open=False)
print("> " + name_fig)

