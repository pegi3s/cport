"""PREDICTPROTEIN module."""
import glob
import logging
import os
import sys
import tempfile
import time
import zipfile

import pandas as pd
from cport.exceptions import ServerConnectionException
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

from cport.modules import utils
from cport.url import PREDICTPROTEIN_URL

log = logging.getLogger("cportlog")

# Total wait (seconds) = WAIT_INTERVAL * NUM_RETRIES
WAIT_INTERVAL = os.environ.get("PREDICTPROTEIN_WAIT_INTERVAL") if os.environ.get("PREDICTPROTEIN_WAIT_INTERVAL") is not None else 10 # seconds
NUM_RETRIES = os.environ.get("PREDICTPROTEIN_NUM_RETRIES") if os.environ.get("PREDICTPROTEIN_NUM_RETRIES") is not None else 12
ELEMENT_LOAD_WAIT = 5  # seconds


class Predictprotein:
    """PREDICTPROTEIN class."""

    def __init__(self, pdb_id, chain_id):
        """
        Initialize the class.

        Parameters
        ----------
        pdb_id : str
            Protein data bank identification code.
        chain_id : str
            Chain identifier.

        """
        self.pdb_id = pdb_id
        self.chain_id = chain_id
        self.wait = int(WAIT_INTERVAL)
        self.tries = int(NUM_RETRIES)

    def submit(self):
        """
        Make a submission to the PredictProtein server.

        Returns
        -------
        html : str
            The html of the submission page.

        """
        fasta_code = utils.get_fasta_from_pdbid(self.pdb_id, self.chain_id)

        # headless so that browser windows are not visually opened and closed
        options = Options()
        options.add_argument("headless")

        # chrome has the most flexibility and ease-of-use
        driver = webdriver.Chrome(chrome_options=options)
        driver.get(PREDICTPROTEIN_URL)

        # identifies the textarea
        elem = driver.find_element_by_id("sequence")
        elem.clear()
        elem.send_keys(fasta_code)

        # selects the specific button for submission
        driver.find_element_by_css_selector(
            "a.btn.btn-submit.btn-primary.btn-large"
        ).click()

        # sleep so that the page is properly loaded before continuing
        time.sleep(ELEMENT_LOAD_WAIT)

        # returns list that is either empty or contains a matching element for
        #  the wait link
        check_link = driver.find_elements_by_xpath(
            '//*[@id="job-monitor-feedback"]/a/span'
        )
        # checks if the list is empty, if empty the url will already be the result url
        if check_link:
            html = check_link[0].get_attribute("innerHTML")
        else:
            html = driver.current_url

        driver.close()

        log.info("Submitted the FASTA sequence to Predict Protein")

        return html

    def retrieve_prediction_file(self, url=None, temp_dir=None):
        """
        Wait for results if necessary and downloads the result file.

        Parameters
        ----------
        url : str
            The url of the prediction.
        temp_dir : str
            The path to a temporary directory.

        Returns
        -------
        temp_dir : str
            The path to the temporary directory containing the precition files.

        """
        options = Options()
        # options to allow pop-up-less downloads
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": temp_dir,
                "profile.default_content_setting_values.automatic_downloads": 2,
            },
        )
        options.add_argument("headless")
        driver = webdriver.Chrome(chrome_options=options)
        driver.get(url)

        completed = False
        while not completed:
            # checks for the binding site button
            try:
                driver.find_element_by_xpath('//*[@id="binding"]/a')
                completed = True
            except NoSuchElementException:
                # still running, wait a bit
                log.debug(f"Waiting for Predict Protein to finish... {self.tries}")
                time.sleep(self.wait)
                driver.refresh()
                self.tries -= 1
            if self.tries == 0:
                # if tries is 0, then the server is not responding
                log.error(f"Predict Protein server is not responding, url was {url}")
                raise ServerConnectionException(f"Predict Protein server is not responding, url was {url}"

        log.info("Retreiving the Predict Protein results")

        time.sleep(ELEMENT_LOAD_WAIT)

        # finds buttons / elements by xpath as css identifier did not work
        # enter used as click did not work
        driver.find_element_by_xpath('//*[@id="binding"]/a').send_keys(Keys.ENTER)
        # sleep to allow the next elements to load as to avoid buttons not being seen
        time.sleep(ELEMENT_LOAD_WAIT)

        # clicks drop down button for download menu
        driver.find_element_by_xpath('//*[@id="Binding"]/div[2]/div/ul/li/a').send_keys(
            Keys.ENTER
        )
        time.sleep(ELEMENT_LOAD_WAIT)

        # clicks raw data download, as opposed to JSON download
        driver.find_element_by_xpath(
            '//*[@id="Binding"]/div[2]/div/ul/li/ul/li[1]/a'
        ).click()
        time.sleep(ELEMENT_LOAD_WAIT)

        driver.close()

        return temp_dir

    @staticmethod
    def parse_prediction(pred_path=None, test_file=None):
        """
        Take the result file and parses them into the prediction dictionary.

        Parameters
        ----------
        pred_path : str
            The path to the directory containing the prediction files.
        test_file : str
            The path to the test file.

        Returns
        -------
        prediction_dict : dict
            The dictionary containing the parsed prediction results with active
            and passive sites.

        """
        prediction_dict = {"active": [], "passive": []}

        if test_file:
            # for testing purposes
            result_file = test_file
        else:
            # returns a list of all zip files, need to specify use of first one
            zip_file = glob.glob(f"{pred_path}/*.zip")[0]
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(f"{pred_path}/")
            os.remove(zip_file)
            result_file = glob.glob(f"{pred_path}/*.prona")[0]

        final_predictions = pd.read_csv(
            result_file,
            skiprows=11,
            usecols=[0, 3],
            names=["Residue_Number", "Protein_Pred"],
            delim_whitespace=True,
        )

        for row in final_predictions.itertuples():
            # 1 indicates interaction
            if row.Protein_Pred == 1:
                interaction = True
            else:
                interaction = False

            residue_number = int(row.Residue_Number.split("_")[-1])
            if interaction:
                prediction_dict["active"].append(residue_number)
            elif not interaction:
                prediction_dict["passive"].append(residue_number)
            else:
                log.warning(
                    f"There appears that residue {row} is either empty or unprocessable"
                )

        return prediction_dict

    def run(self):
        """
        Execute the PredictProtein prediction.

        Returns
        -------
        prediction_dict : dict
            A dictionary containing the raw prediction results.

        """
        log.info("Running PredictProtein")
        log.info(f"Will try {self.tries} times waiting {self.wait}s between tries")

        submitted_url = self.submit()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_prediction = self.retrieve_prediction_file(
                url=submitted_url, temp_dir=temp_dir
            )
            prediction_dict = self.parse_prediction(pred_path=temp_dir_prediction)

        return prediction_dict
