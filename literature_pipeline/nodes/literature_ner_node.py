from typing import List, Dict
from ..schemas import PipelineState, Article, ArticleReflection, ReflectionBatch
from ..tools.full_text_retrieval import retrieve_article
import logging
