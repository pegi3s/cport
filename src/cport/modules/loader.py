"""Load predictors to run."""
import logging
from functools import partial

from cport.modules.cons_ppisp import ConsPPISP
from cport.modules.error import IncompleteInputError
from cport.modules.ispred4 import Ispred4
from cport.modules.meta_ppisp import MetaPPISP
from cport.modules.predictprotein_api import Predictprotein
from cport.modules.predus2 import Predus2
from cport.modules.scriber import Scriber
from cport.modules.sppider import Sppider
from cport.modules.whiscy import Whiscy

log = logging.getLogger("cportlog")


def run_whiscy(pdb_id, chain_id):
    """
    Run the WHISCY predictor.

    Parameters
    ----------
    pdb_id : str
        Protein data bank identification code.
    chain_id : str
        Chain identifier.

    Returns
    -------
    predictions : dict
        Dictionary containing the predictions

    """
    whiscy = Whiscy(pdb_id, chain_id)
    predictions = whiscy.run()
    log.info(predictions)
    return predictions


def run_ispred4(pdb_id, chain_id):
    """
    Run the ISPRED4 predictor.

    Parameters
    ----------
    pdb_id : str
        Protein data bank identification code.
    chain_id : str
        Chain identifier.

    Returns
    -------
    predictions : dict
        Dictionary containing the predictions

    """
    ispred4 = Ispred4(pdb_id, chain_id)
    predictions = ispred4.run()
    log.info(predictions)
    return predictions


def run_scriber(pdb_id, chain_id):
    """
    Run the SCRIBER predictor.

    Parameters
    ----------
    pdb_id : str
        Protein data bank identification code.
    chain_id : str
        Chain identifier.

    Returns
    -------
    predictions : dict
        Dictionary containing the predictions

    """
    scriber = Scriber(pdb_id, chain_id)
    predictions = scriber.run()
    log.info(predictions)
    return predictions


def run_sppider(pdb_id, chain_id):
    """
    Run the WHISCY predictor.

    Parameters
    ----------
    pdb_id : str
        Protein data bank identification code.
    chain_id : str
        Chain identifier.

    Returns
    -------
    predictions : dict
        Dictionary containing the predictions

    """
    sppider = Sppider(pdb_id, chain_id)
    predictions = sppider.run()
    log.info(predictions)
    return predictions


def run_cons_ppisp(pdb_id, chain_id):
    """
    Run the CONS-PPISP predictor.

    Parameters
    ----------
    pdb_id : str
        Protein data bank identification code.
    chain_id : str
        Chain identifier.

    Returns
    -------
    predictions : dict
        Dictionary containing the predictions

    """
    cons_ppisp = ConsPPISP(pdb_id, chain_id)
    predictions = cons_ppisp.run()
    log.info(predictions)
    return predictions


def run_meta_ppisp(pdb_id, chain_id):
    """
    Run the META-PPISP predictor.

    Parameters
    ----------
    pdb_id : str
        Protein data bank identification code.
    chain_id : str
        Chain identifier.

    Returns
    -------
    predictions : dict
        Dictionary containing the predictions

    """
    meta_ppisp = MetaPPISP(pdb_id, chain_id)
    predictions = meta_ppisp.run()
    log.info(predictions)
    return predictions


def run_predus2(pdb_id, chain_id):
    """
    Run the WHISCY predictor.

    Parameters
    ----------
    pdb_id : str
        Protein data bank identification code.
    chain_id : str
        Chain identifier.

    Returns
    -------
    predictions : dict
        Dictionary containing the predictions

    """
    predus2 = Predus2(pdb_id, chain_id)
    predictions = predus2.run()
    log.info(predictions)
    return predictions


def run_predictprotein(pdb_id, chain_id):
    """
    Run the PREDICTPROTEIN predictor.

    Parameters
    ----------
    pdb_id : str
        Protein data bank identification code.
    chain_id : str
        Chain identifier.

    Returns
    -------
    predictions : dict
        Dictionary containing the predictions

    """
    predictprotein_api = Predictprotein(pdb_id, chain_id)
    predictions = predictprotein_api.run()
    log.info(predictions)
    return predictions


def run_placeholder(fasta_str):
    """
    Run the PLACEHOLDER predictor.

    Parameters
    ----------
    fasta_str : str
        Fasta string.

    """
    log.info("Placeholder predictor")
    log.info(f"fasta_str: {fasta_str}")


PDB_PREDICTORS = {
    "cons_ppisp": run_cons_ppisp,
    "ispred4": run_ispred4,
    "meta_ppisp": run_meta_ppisp,
    "predictprotein": run_predictprotein,
    "predus2": run_predus2,
    "scriber": run_scriber,
    "sppider": run_sppider,
    "whiscy": run_whiscy,
}

FASTA_PREDICTORS = {"placeholder": run_placeholder}


def run_prediction(prediction_method, **kwargs):
    """
    Select predictors to run.

    Parameters
    ----------
    prediction_method : str
        Prediction method to be run.
    kwargs : dict
        Keyword arguments.

    Returns
    -------
    result : dict
        Dictionary containing the predictions


    Raises
    ------
    IncompleteInputError
        If the input is incomplete.
    ValueError
        If the prediction method is not supported.

    """
    if prediction_method in PDB_PREDICTORS:
        if not kwargs["pdb_id"]:
            raise IncompleteInputError(
                predictor_name=prediction_method, missing="pdb_id"
            )

        if not kwargs["chain_id"]:
            raise IncompleteInputError(
                predictor_name=prediction_method, missing="chain_id"
            )

        predictor_func = partial(
            PDB_PREDICTORS[prediction_method],
            pdb_id=kwargs["pdb_id"],
            chain_id=kwargs["chain_id"],
        )

    elif prediction_method in FASTA_PREDICTORS:
        if not kwargs["fasta_file"]:
            raise IncompleteInputError(
                predictor_name=prediction_method, missing="fasta_file"
            )
        predictor_func = partial(
            FASTA_PREDICTORS[prediction_method], fasta_str=kwargs["fasta_file"]
        )
    else:
        raise ValueError(f"Unknown prediction method: {prediction_method}")

    log.info(f"Running method: {prediction_method}")

    result = predictor_func()

    return result
