import logging

from hdx.scraper.base_scraper import BaseScraper
from hdx.utilities.dictandlist import dict_of_lists_add

logger = logging.getLogger(__name__)


class IOMDTM(BaseScraper):
    def __init__(self, datasetinfo, today, admintwo):
        super().__init__(
            "iom_dtm",
            datasetinfo,
            {"admintwo": (("IDPs",), ("#affected+idps+ind",))},
        )
        self.today = today
        self.admintwo = admintwo

    def run(self) -> None:
        iom_url = self.datasetinfo["url"]
        reader = self.get_reader()
        headers, iterator = reader.get_tabular_rows(
            iom_url, headers=1, dict_form=True, format="csv"
        )
        rows = list(iterator)
        idpsdict = dict()
        for ds_row in rows:
            countryiso3 = ds_row["Country ISO"]
            dataset_name = ds_row["Dataset Name"]
            if not dataset_name:
                logger.warning(f"No IOM DTM data for {countryiso3}.")
                continue
            dataset = reader.read_dataset(dataset_name)
            if not dataset:
                logger.warning(f"No IOM DTM data for {countryiso3}.")
                continue
            resource = dataset.get_resource()
            data = reader.read_hxl_resource(countryiso3, resource, "IOM DTM data")
            if data is None:
                continue
            pcodes_found = False
            for row in data:
                pcode = row.get("#adm2+code")
                if not pcode:
                    adm2name = row.get("#adm2+name")
                    if adm2name:
                        pcode, _ = self.admintwo.get_pcode(
                            countryiso3, adm2name, "iom_dtm"
                        )
                if not pcode:
                    location = row.get("#loc")
                    if location:
                        location = location.split(">")[-1]
                        pcode, _ = self.admintwo.get_pcode(
                            countryiso3, location, "iom_dtm"
                        )
                if pcode:
                    pcode = pcode.strip().upper()
                    idps = row.get("#affected+idps+ind")
                    if idps:
                        dict_of_lists_add(idpsdict, f"{countryiso3}:{pcode}", idps)
                    pcodes_found = True
            if not pcodes_found:
                logger.warning(f"No pcodes found for {countryiso3}.")

        idps = self.get_values("admintwo")[0]
        for countrypcode in idpsdict:
            countryiso3, pcode = countrypcode.split(":")
            if pcode not in self.admintwo.pcodes:
                logger.error(f"PCode {pcode} in {countryiso3} does not exist!")
            else:
                idps[pcode] = sum(idpsdict[countrypcode])
        self.datasetinfo["source_date"] = self.today
        self.datasetinfo["source_url"] = iom_url
