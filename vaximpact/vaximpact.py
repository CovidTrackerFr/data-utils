# coding: utf-8
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import json
import logging
from pathlib import Path
import os
import pytz
from statistics import mean
PATH = os.getcwd() + "/vaximpact/"

logging.basicConfig(format="%(asctime)-15s %(message)s")
logger = logging.getLogger("VaxImpact-Data")
logger.setLevel(logging.INFO)


def get_config():
    with open(PATH + "config_vaximpact.json", "r", encoding="UTF-8") as config_file:
        config = json.load(config_file)
    return config


DICT_INSEE_POP = get_config().get("population")

# Qui prendre en compte dans les vaccinés ?
# Groupes disponibles = "Vaccination complète", "Non-vaccinés" "Primo dose efficace", "Primo dose récente"

VACCINES_3_DOSES = {"label": "vaccinés avec rappel", "data": get_config().get("groupe_vaccinés_3_doses", None)}
VACCINES_2_DOSES = {"label": "vaccinés sans rappel", "data": get_config().get("groupe_vaccinés_2_doses", None)}
NON_VACCINES = {"label": "non vaccinés", "data": get_config().get("groupe_non_vaccinés", None)}

# Groupes d'âge
AGE = get_config().get("age_categories")
ROUND_DECIMAL = get_config().get("round_to_decimal", 2)

if not DICT_INSEE_POP or not VACCINES_3_DOSES or not VACCINES_2_DOSES or not NON_VACCINES:
    logger.error("[ERROR] - Check config file accessibility and variables.")
    exit(1)


def get_start_and_end_date_from_calendar_week(year, calendar_week):
    monday = datetime.strptime(f"{year}-{calendar_week}-1", "%Y-%W-%w").date()
    return monday, monday + timedelta(days=6.9)


def export_results_json(content, file_name, region_trigram):
    Path(PATH + f"output_age/{region_trigram}").mkdir(parents=True, exist_ok=True)
    with open(PATH + f"output_age/{region_trigram}/{file_name}.json", "w", encoding="UTF-8") as outfile:
        json.dump(content, outfile, indent=2, ensure_ascii=False)
    logger.debug(f"[SUCCESS] - File {file_name} has been exported.")


class Vaximpact:
    def __init__(
        self, api_name, api_url, trigram, groupe_non_vaccinés, groupe_vaccinés_2_doses, groupe_vaccinés_3_doses
    ):
        self.api_name = api_name
        self.api_url = api_url
        self.trigram = trigram
        self.groupe_vaccinés_2_doses = groupe_vaccinés_2_doses["data"]
        self.groupe_vaccinés_2_doses_label = groupe_vaccinés_2_doses["label"]
        self.groupe_vaccinés_3_doses = groupe_vaccinés_3_doses["data"]
        self.groupe_vaccinés_3_doses_label = groupe_vaccinés_3_doses["label"]

        self.groupe_non_vaccinés = groupe_non_vaccinés["data"]
        self.groupe_non_vaccinés_label = groupe_non_vaccinés["label"]
        if trigram == "FR":
            self.toutelafrance = True
        else:
            self.toutelafrance = False

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
        age = None

        sum_by_week = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
        )
        omicron_mean = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
        )
        for record in self.api_records:
            if self.toutelafrance:
                age = record["fields"]["age"]

            vac_statut = record["fields"]["vac_statut"]
            if vac_statut in self.groupe_vaccinés_2_doses:
                vac_statut = self.groupe_vaccinés_2_doses_label
            elif vac_statut in self.groupe_non_vaccinés:
                vac_statut = self.groupe_non_vaccinés_label
            elif vac_statut in self.groupe_vaccinés_3_doses:
                vac_statut = self.groupe_vaccinés_3_doses_label
            year_iso_number = str(datetime.fromisoformat(record["fields"]["date"]).isocalendar()[0])
            week_iso_number = str(datetime.fromisoformat(record["fields"]["date"]).isocalendar()[1])
            if len(week_iso_number)==1:
                week_iso_number=f"0{week_iso_number}"
     

            first_day, last_day = get_start_and_end_date_from_calendar_week(year_iso_number, week_iso_number)
            week_number = f"{year_iso_number}{week_iso_number}"
            sum_by_week[week_number]["start_date"] = str(first_day)
            sum_by_week[week_number]["end_date"] = str(last_day)

            # Le dernier jour de la semaine, l'effectif J-7 correspond environ à l'effectif en début de semaine.
            if str(record["fields"]["date"]) == str(last_day):
                sum_by_week[week_number]["data"]["all"][vac_statut]["effectif"] += record["fields"]["effectif"]
                if self.toutelafrance:
                    sum_by_week[week_number]["data"][age][vac_statut]["effectif"] += record["fields"]["effectif"]
                else:
                    sum_by_week[week_number]["data"]["all"]["Ensemble"]["effectif"] += record["fields"]["effectif"]

            for a in record["fields"].keys():
                if "date" in a or "vac_statut" in a or "effectif" in a or "region" in a or "age" in a :
                    continue

                if "pcr_pourcent_omicron" in a or "hc_pourcent_omicron" in a or "sc_pourcent_omicron" in a or "dc_pourcent_omicron" in a or "pcr_sympt_pourcent_omicron" in a:
                    if record["fields"][a]=="NA":
                        continue
                    omicron_mean[week_number]["data"][age][vac_statut][a].append(float(record["fields"][a]))
                    sum_by_week[week_number]["data"][age][vac_statut][a] = mean(omicron_mean[week_number]["data"][age][vac_statut][a])
                    continue

                sum_by_week[week_number]["data"]["all"][vac_statut][a] += float(record["fields"][a])
                if self.toutelafrance:
                    sum_by_week[week_number]["data"][age][vac_statut][a] += float(record["fields"][a])

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
            age_list = {}
            for age, age_data in week["data"].items():
                end_date = None
                start_date = week["start_date"]
                end_date = week["end_date"]

                byinjtype = {}
                for (groupe_1_label, groupe_2_label) in [
                    (self.groupe_vaccinés_2_doses_label, self.groupe_non_vaccinés_label),
                    (self.groupe_vaccinés_3_doses_label, self.groupe_vaccinés_2_doses_label),
                    (self.groupe_vaccinés_3_doses_label, self.groupe_non_vaccinés_label),
                ]:
                    event_list = {}

                    for data_name, data_code in data_type.items():
                        pop_ref = None
                        risque_relatif = None
                        FER_exposes = None
                        FER_population = None

                        if isinstance(data_code, dict):
                            pop_ref = data_code["pop_ref"]
                            data_code = data_code["data"]

                        if (
                            age_data[groupe_1_label][f"{data_code}"] == 0
                            or age_data[groupe_2_label][f"{data_code}"] == 0
                            or not age_data[groupe_1_label]["effectif"]
                            or age_data[groupe_1_label]["effectif"] == 0
                            or not age_data[groupe_2_label]["effectif"]
                            or age_data[groupe_2_label]["effectif"] == 0
                        ):
                            event_list[f"{data_name}"] = {
                                "risque_relatif": -1,
                                "FER_exposes": -1,
                                "FER_population": -1,
                            }
                            continue

                        elif pop_ref:
                            if (
                                not age_data[groupe_1_label][f"{pop_ref}"]
                                or age_data[groupe_1_label][f"{pop_ref}"] == 0
                                or not age_data[groupe_2_label][f"{pop_ref}"]
                                or age_data[groupe_2_label][f"{pop_ref}"] == 0
                            ):
                                event_list[f"{data_name}"] = {
                                    "risque_relatif": -1,
                                    "FER_exposes": -1,
                                    "FER_population": -1,
                                }
                                continue

                            risque_relatif = round(
                                (age_data[groupe_2_label][f"{data_code}"] / age_data[groupe_2_label][f"{pop_ref}"])
                                / (age_data[groupe_1_label][f"{data_code}"] / age_data[groupe_1_label][f"{pop_ref}"]),
                                ROUND_DECIMAL,
                            )
                            if risque_relatif!=0:
                                FER_exposes = round(((risque_relatif - 1) / risque_relatif) * 100, ROUND_DECIMAL)
                            FER_population = round(
                                (
                                    FER_exposes
                                    * (
                                        age_data[groupe_2_label][f"{data_code}"]
                                        / (
                                            age_data[groupe_2_label][f"{data_code}"]
                                            + age_data[groupe_1_label][f"{data_code}"]
                                        )
                                    )
                                ),
                                ROUND_DECIMAL,
                            )
                            event_list[f"{data_name}"] = {
                                "risque_relatif": risque_relatif,
                                "FER_exposes": -1,
                                "FER_population": -1,
                            }

                        else:
                            risque_relatif = round(
                                (
                                    (
                                        age_data[groupe_2_label][f"{data_code}"]
                                        / age_data[groupe_1_label][f"{data_code}"]
                                    )
                                    * (age_data[groupe_1_label]["effectif"] / age_data[groupe_2_label]["effectif"])
                                ),
                                ROUND_DECIMAL,
                            )
                            FER_exposes = round(((risque_relatif - 1) / risque_relatif) * 100, ROUND_DECIMAL)
                            FER_population = round(
                                (
                                    FER_exposes
                                    * (
                                        age_data[groupe_2_label][f"{data_code}"]
                                        / (
                                            age_data[groupe_2_label][f"{data_code}"]
                                            + age_data[groupe_1_label][f"{data_code}"]
                                        )
                                    )
                                ),
                                ROUND_DECIMAL,
                            )

                        event_list[f"{data_name}"] = {
                            "risque_relatif": risque_relatif,
                            "FER_exposes": FER_exposes,
                            "FER_population": FER_population,
                        }
                    byinjtype[f"{groupe_1_label} vs {groupe_2_label}"] = event_list
                age_list[age] = byinjtype
            stats_by_week[week_number] = {
                "week_start_date": start_date,
                "week_end_date": end_date,
                "data": age_list,
            }

        global_dict["last_updated"] = (
            datetime.today().astimezone(tz=pytz.timezone("Europe/Paris")).strftime("%Y/%m/%d %H:%M:%S")
        )

        global_dict["data_by_week"] = {key: value for (key, value) in sorted(stats_by_week.items())}
        logger.info(f"[SUCCESS] - Statistics for {self.api_name} have been rendered.")

        return global_dict


def main():
    france_api = get_config().get("france_api", None)
    region_api = get_config().get("region_api", None)
    regions_list = get_config().get("regions", None)

    # Regions
    for region_trigram, region_full_name in regions_list.items():
        table_return = {}
        regions_data = Vaximpact(
            region_full_name,
            region_api.format(region=region_trigram),
            region_trigram,
            NON_VACCINES,
            VACCINES_2_DOSES,
            VACCINES_3_DOSES,
        )

        table, stats = regions_data.render_stats()
        table_return["last_updated"] = (
            datetime.today().astimezone(tz=pytz.timezone("Europe/Paris")).strftime("%d/%m/%Y %H:%M:%S")
        )
        table_return["data_by_week"] = {key: value for (key, value) in sorted(table.items())}

        export_results_json(table_return, f"data_by_week", region_trigram)
        export_results_json(stats, f"stats_by_week", region_trigram)

    # France
    table_return = {}
    france_data = Vaximpact("France", france_api, "FR", NON_VACCINES, VACCINES_2_DOSES, VACCINES_3_DOSES)

    table, stats = france_data.render_stats()
    table_return["last_updated"] = (
        datetime.today().astimezone(tz=pytz.timezone("Europe/Paris")).strftime("%d/%m/%Y %H:%M:%S")
    )
    table_return["data_by_week"] = {key: value for (key, value) in sorted(table.items())}

    export_results_json(table_return, f"data_by_week", "FR")
    export_results_json(stats, f"stats_by_week", "FR")

    exit(0)


if __name__ == "__main__":
    main()
