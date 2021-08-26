 # coding: utf-8
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import json
import logging
from pathlib import Path
import os

PATH = os.getcwd() + "/vaximpact/"

logging.basicConfig(format="%(asctime)-15s %(message)s")
logger = logging.getLogger("VaxImpact-Data")
logger.setLevel(logging.INFO)


def get_config():
    with open(PATH+"config_vaximpact.json", "r", encoding="UTF-8") as config_file:
        config = json.load(config_file)
    return config


YEAR = get_config().get("year", None)
DICT_INSEE_POP = get_config().get("population")

# Qui prendre en compte dans les vaccinés ?
# Groupes disponibles = "Vaccination complète", "Non-vaccinés" "Primo dose efficace", "Primo dose récente"

VACCINES = get_config().get("groupe_vaccinés", None)
NON_VACCINES = get_config().get("groupe_non_vaccinés", None)

ROUND_DECIMAL = get_config().get("round_to_decimal", 2)

if not YEAR or not DICT_INSEE_POP or not VACCINES or not NON_VACCINES:
    logger.error("[ERROR] - Check config file accessibility and variables.")
    exit(1)


def get_start_and_end_date_from_calendar_week(year, calendar_week):
    monday = datetime.strptime(f"{year}-{calendar_week}-1", "%Y-%W-%w").date()
    return monday, monday + timedelta(days=6.9)


def export_results_json(content, file_name, region_trigram):
    Path(PATH+f"output/{region_trigram}").mkdir(parents=True, exist_ok=True)
    with open(PATH+f"output/{region_trigram}/{file_name}.json", "w", encoding="UTF-8") as outfile:
        json.dump(content, outfile, indent=2, ensure_ascii=False)
    logger.debug(f"[SUCCESS] - File {file_name} has been exported.")


class Vaximpact:
    def __init__(self, api_name, api_url, trigram):
        self.api_name = api_name
        self.api_url = api_url
        self.trigram = trigram

    def render_stats(self):
        self.api_records = self.access_api()
        self.week_table = self.build_sum_by_week()
        self.stats_by_week = self.calculate_stats()
        return self.week_table, self.stats_by_week

    def access_api(self):
        try:
            r = requests.get(self.api_url)
            r.raise_for_status()
            output = r.json()

            if output["nhits"] == 0:
                raise

        except:
            logger.error(f"[ERROR] - Can't access DREES {self.api_name} API.")
            exit(1)

        records = output["records"]
        logger.debug(f"[SUCCESS] - Successfully downloaded data from DREES {self.api_name} API.")

        return records

    def build_sum_by_week(self):
        sum_by_week = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for record in self.api_records:
            vac_statut = record["fields"]["vac_statut"]
            if vac_statut in VACCINES:
                vac_statut = "Vaccinés"
            elif vac_statut in NON_VACCINES:
                vac_statut = "Pas_vaccinés"
            else:
                continue
            week_iso_number = datetime.fromisoformat(record["fields"]["date"]).isocalendar()[1]
            first_day, last_day = get_start_and_end_date_from_calendar_week(YEAR, week_iso_number)
            week_number = f"{YEAR}{week_iso_number}"
            sum_by_week[week_number]["start_date"] = str(first_day)
            sum_by_week[week_number]["end_date"] = str(last_day)

            # Le dernier jour de la semaine, l'effectif J-7 correspond environ à l'effectif en début de semaine.
            if str(record["fields"]["date"]) == str(last_day):
                sum_by_week[week_number][vac_statut]["effectif_j_7"] += record["fields"]["effectif_j_7"]

            for a in record["fields"].keys():
                if "date" in a or "vac_statut" in a or "effectif_j_7" in a or "region" in a:
                    continue
                sum_by_week[week_number][vac_statut][a] += record["fields"][a]

        logger.debug(f"[SUCCESS] - Successfully built data table {self.api_name}.")
        return sum_by_week

    def calculate_stats(self):
        global_dict = {}
        if self.trigram == "FR":
            data_type = get_config().get("data_type_france", None)
        else:
            data_type = get_config().get("data_type_regions", None)
        stats_by_week = {}

        for week_number, week in self.week_table.items():
            end_date = None

            start_date = week["start_date"]
            end_date = week["end_date"]

            taille_population = DICT_INSEE_POP[self.trigram]
            vaccination_rate = round((week["Vaccinés"]["effectif_j_7"] / taille_population) * 100, ROUND_DECIMAL)
            event_list = {}
            
            for data_name, data_code in data_type.items():
                pop_ref = None
                if isinstance(data_code, dict):
                    pop_ref = data_code["pop_ref"]
                    data_code=data_code["data"]
                if week["Vaccinés"][f"{data_code}"] == 0:
                    risque_relatif = f"Non calculable - 0 {data_name} chez vaccinés"
                    if week["Pas_vaccinés"][f"{data_code}"] == 0:
                        FER_exposes = f"Non calculable - 0 {data_name} chez Non-vaccinés ni chez Vaccinés"
                        FER_population = f"Non calculable - 0 {data_name} chez Non-vaccinés ni chez Vaccinés"
                    else:
                        FER_exposes = 100
                        FER_population = round((FER_exposes * (week["Pas_vaccinés"][f"{data_code}"] / (week["Pas_vaccinés"][f"{data_code}"] + week["Vaccinés"][f"{data_code}"]))), ROUND_DECIMAL)

                elif week["Pas_vaccinés"][f"{data_code}"] == 0:
                    risque_relatif = f"Non calculable - 0 {data_name} chez Non-vaccinés"
                    FER_exposes = f"Non calculable - 0 {data_name} chez Non-vaccinés"
                    FER_population = f"Non calculable - 0 {data_name} chez Non-vaccinés"

                else:
                    if pop_ref:
                        risque_relatif = round(((week["Pas_vaccinés"][f"{data_code}"] / week["Vaccinés"][f"{data_code}"]) * (week["Vaccinés"][f"{pop_ref}"] / week["Pas_vaccinés"][f"{pop_ref}"])), ROUND_DECIMAL)
                        FER_exposes = round(((risque_relatif - 1) / risque_relatif) * 100, ROUND_DECIMAL)
                        FER_population = round((FER_exposes * (week["Pas_vaccinés"][f"{data_code}"] / (week["Pas_vaccinés"][f"{data_code}"] + week["Vaccinés"][f"{data_code}"]))), ROUND_DECIMAL)

                    else:
                        risque_relatif = round(((week["Pas_vaccinés"][f"{data_code}"] / week["Vaccinés"][f"{data_code}"]) * (week["Vaccinés"]["effectif_j_7"] / week["Pas_vaccinés"]["effectif_j_7"])), ROUND_DECIMAL)
                        FER_exposes = round(((risque_relatif - 1) / risque_relatif) * 100, ROUND_DECIMAL)
                        FER_population = round((FER_exposes * (week["Pas_vaccinés"][f"{data_code}"] / (week["Pas_vaccinés"][f"{data_code}"] + week["Vaccinés"][f"{data_code}"]))), ROUND_DECIMAL)

                event_list[f"{data_name}"] = {"risque_relatif": risque_relatif, "FER_exposes": FER_exposes, "FER_population": FER_population}
            stats_by_week[week_number] = {"week_start_date": start_date, "week_end_date": end_date, "vaccination_rate": vaccination_rate, "data": event_list}
            
        global_dict["last_updated"] = datetime.today().strftime("%d/%m/%Y %H:%M:%S")
        global_dict["data_by_week"] = {key: value for (key, value) in sorted(stats_by_week.items())}
        logger.info(f"[SUCCESS] - Statistics for {self.api_name} have been rendered.")

        return global_dict


def main():
    france_api = get_config().get("france_api", None)
    region_api = get_config().get("region_api", None)

    regions_list = get_config().get("regions", None)

    for region_trigram, region_full_name in regions_list.items():
        table_return = {}
        if region_trigram == "FR":
            api = france_api
        else:
            api = region_api.format(region=region_trigram)

        vaximpact = Vaximpact(region_full_name, api, region_trigram)

        table, stats = vaximpact.render_stats()
        table_return["last_updated"] = datetime.today().strftime("%d/%m/%Y %H:%M:%S")
        table_return["data_by_week"] = {key: value for (key, value) in sorted(table.items())}

        export_results_json(table_return, f"data_by_week", region_trigram)
        export_results_json(stats, f"stats_by_week", region_trigram)

    exit(0)


if __name__ == "__main__":
    main()
