"""Rotating local diagnostics; never records bridge credentials or request payloads."""
import logging,os,tempfile
from pathlib import Path
from logging.handlers import RotatingFileHandler

def configure():
    logger=logging.getLogger('mine2blend')
    if not logger.handlers:
        folder=Path(tempfile.gettempdir())/'Mine2Blend'/'logs';folder.mkdir(parents=True,exist_ok=True)
        handler=RotatingFileHandler(folder/f'editor-{os.getpid()}.log',maxBytes=2_000_000,backupCount=3,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(threadName)s %(message)s'))
        logger.addHandler(handler);logger.setLevel(logging.INFO)
    return logger
