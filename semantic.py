"""Optional local sentence embeddings; never download during a web request."""
from pathlib import Path
import json
import logging
import os
import numpy as np

MODEL_ID = 'sentence-transformers/all-MiniLM-L6-v2'
log = logging.getLogger(__name__)


class SemanticEncoder:
    def __init__(self, mode='off', model_dir=None):
        self.model = None
        self.cache = {}
        self.reason = 'Sentence embeddings are disabled.'
        if mode == 'off':
            return
        if not model_dir or not (Path(model_dir) / 'modules.json').is_file():
            self.reason = 'The optional sentence model is not installed. TF-IDF and contextual synonyms are active.'
            return
        try:
            import torch
            torch.set_num_threads(min(2,os.cpu_count() or 1))
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(str(model_dir),device='cpu',local_files_only=True,
                                              trust_remote_code=False,model_kwargs={'use_safetensors':True})
            self.model.max_seq_length = 256
            self.reason = 'Local MiniLM sentence embeddings are active.'
        except Exception as error:
            self.reason = f'Sentence embeddings unavailable ({type(error).__name__}); TF-IDF and contextual synonyms are active.'
            log.warning(self.reason)

    def similarities(self, texts):
        if self.model is None:
            return None
        try:
            missing=list(dict.fromkeys(text for text in texts if text not in self.cache))
            if missing:
                encoded=self.model.encode(missing,batch_size=32,normalize_embeddings=True,show_progress_bar=False)
                self.cache.update((text,np.asarray(vector)) for text,vector in zip(missing,encoded))
            vectors = np.asarray([self.cache[text] for text in texts])
            if len(self.cache)>512:
                self.cache={text:self.cache[text] for text in texts[-512:]}
            return np.clip(vectors[1:] @ vectors[0],0,1).tolist()
        except Exception as error:
            self.model = None
            self.reason = f'Sentence inference unavailable ({type(error).__name__}); fallback is active.'
            log.warning(self.reason)
            return None

    def status(self):
        return {'mode':'semantic' if self.model is not None else 'fallback',
                'label':'Sentence embeddings + TF-IDF + attributes' if self.model is not None else 'TF-IDF + contextual synonyms + attributes',
                'model':MODEL_ID if self.model is not None else None,'detail':self.reason}


def prepare_model(destination):
    """An explicit operator action requiring internet, never an application startup side effect."""
    from huggingface_hub import model_info, snapshot_download
    info = model_info(MODEL_ID)
    destination = Path(destination)
    snapshot_download(repo_id=MODEL_ID,revision=info.sha,local_dir=str(destination),
        allow_patterns=['*.json','*.txt','*.safetensors','1_Pooling/*'])
    (destination / 'findly-model.json').write_text(json.dumps({'model':MODEL_ID,'revision':info.sha},indent=2),encoding='utf-8')
    encoder = SemanticEncoder('auto',destination)
    if encoder.model is None or encoder.similarities(['a water bottle','a reusable drinking flask']) is None:
        raise RuntimeError(encoder.reason)
    return encoder.status()
