"""PSIVER module."""
# This predictor can take up to 5 hours to complete,
# so similar to meta-ppisp its reliability should be
# examined before it gets added to the final prediction.
import gzip
import logging
import re
import sys
import tempfile
import time
import os

from io import StringIO

from cport.exceptions import ServerConnectionException
import mechanicalsoup as ms
import pandas as pd
import requests

from cport.modules.utils import get_fasta_from_pdbfile
from cport.url import PSIVER_URL

log = logging.getLogger("cportlog")

# Total wait (seconds) = WAIT_INTERVAL * NUM_RETRIES
WAIT_INTERVAL = os.environ.get("PSIVER_WAIT_INTERVAL") if os.environ.get("PSIVER_WAIT_INTERVAL") is not None else 60 # seconds
NUM_RETRIES = os.environ.get("PSIVER_NUM_RETRIES") if os.environ.get("PSIVER_NUM_RETRIES") is not None else 300


class Psiver:
    """PSIVER class."""

    def __init__(self, pdb_file, chain_id):
        """
        Initialize the class.

        Parameters
        ----------
        pdb_file : str
            Path to PDB file.
        chain_id : str
            Chain identifier.

        """
        self.pdb_file = pdb_file
        self.chain_id = chain_id
        self.wait = int(WAIT_INTERVAL)
        self.tries = int(NUM_RETRIES)

    def submit(self):
        """
        Make a submission to the PSIVER server.

        Returns
        -------
        submission_link: str
            url resulting from submission.

        """
        sequence = get_fasta_from_pdbfile(self.pdb_file, self.chain_id)

        browser = ms.StatefulBrowser()
        browser.open(PSIVER_URL)

        input_form = browser.select_form(nr=0)
        input_form.set_textarea({"fasta_seq": sequence})
        browser.submit_selected()

        wait_page = str(browser.page)
        # https://regex101.com/r/Mo8rwL/1
        wait_link = re.findall(r"href=\"(.*)\"</script", wait_page)[0]

        return wait_link

    def retrieve_prediction_link(self, url=None, page_text=None):
        """
        Retrieve the link to the PSIVER prediction page.

        Parameters
        ----------
        url : str
            The url of the PSIVER processing page.
        page_text : str
            The text of the PSIVER processing page.

        Returns
        -------
        url : str
            The url of the obtained PSIVER prediction page.

        """
        browser = ms.StatefulBrowser()

        if page_text:
            # this is used in the testing
            browser.open_fake_page(page_text=page_text)
            url = page_text
        else:
            browser.open(url)

        completed = False
        while not completed:
            # Check if the result page exists
            match = re.search(r"All the results are available now.", str(browser.page))
            if match:
                completed = True
            else:
                # still running, wait a bit
                log.debug(f"Waiting for PSIVER to finish... {self.tries}")
                time.sleep(self.wait)
                browser.refresh()
                self.tries -= 1

            if self.tries == 0:
                # if tries is 0, then the server is not responding
                log.error(f"PSIVER server is not responding, url was {url}")
                raise ServerConnectionException(f"PSIVER server is not responding, url was {url}")

        if page_text:
            final_url = url
        else:
            result_link = browser.links()[4]
            browser.follow_link(result_link)

            download_link = browser.links()[1]
            browser.follow_link(download_link)
            final_url = browser.url

        return final_url

    @staticmethod
    def download_result(download_link):
        """
        Download the results.

        Parameters
        ----------
        download_link : str
            The url of the PSIVER result page.

        Returns
        -------
        temp_file.name : str
            The name of the temporary file containing the results.

        """
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(requests.get(download_link).content)
        return temp_file.name

    def parse_prediction(self, pred_url=None, test_file=None):
        """
        Take the results extracts the active and passive residue predictions.

        Parameters
        ----------
        pred_url : str
            The url of the PSIVER result page.
        test_file : str
            A file containing the text present in the result page

        Returns
        -------
        prediction_dict : dict
            A dictionary containing the active and passive residue predictions.

        """
        prediction_dict = {"active": [], "passive": []}

        if test_file:
            # for testing purposes
            result_file = test_file
        else:
            download_file = self.download_result(pred_url)
            with gzip.open(download_file, "rt") as unzip_file:
                file_content = unzip_file.read()
            result_file = StringIO(file_content)

        final_predictions = pd.read_csv(
            result_file,
            engine="python",
            header=None,
            skiprows=15,
            usecols=[0, 1, 2, 4],
            names=["check", "residue", "prediction", "score"],
            delim_whitespace=True,
        )

        for row in final_predictions.itertuples():
            # skips bottom rows as this number can vary between results
            if row.check != "PRED":
                continue
            if row.prediction == "-":
                interaction = False
            else:
                interaction = True
            
            score = row.score

            residue_number = row.residue
            if interaction:
                prediction_dict["active"].append([int(residue_number), float(score)])
            elif not interaction:
                prediction_dict["passive"].append([int(residue_number), float(score)])
            else:
                log.warning(
                    f"There appears that residue {row} is either empty or unprocessable"
                )

        return prediction_dict

    def run(self):
        """
        Execute the PSIVER prediction.

        Returns
        -------
        prediction_dict : dict
            A dictionary containing the active and passive residue predictions.

        """
        log.info("Running PSIVER")
        log.info(f"Will try {self.tries} times waiting {self.wait}s between tries")

        submitted_url = self.submit()
        prediction_url = self.retrieve_prediction_link(url=submitted_url)
        prediction_dict = self.parse_prediction(pred_url=prediction_url)

        return prediction_dict
