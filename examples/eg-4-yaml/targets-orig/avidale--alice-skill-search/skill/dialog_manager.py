import logging

from skill import nlg, nlu
import random
import dialogic
import yaml

from dialogic.dialog_manager import BaseDialogManager
from nanosearch.custom_engine import SkillEngine


logger = logging.getLogger(__name__)


class SearcherDialogManager(BaseDialogManager):
    def __init__(
            self,
            engine: SkillEngine,
            faq_file='config/faq.yaml',
            intents_file='config/intents.yaml'
    ):
        super(SearcherDialogManager, self).__init__()
        self.engine = engine

        with open(intents_file, 'r', encoding='utf-8') as f:
            intents = yaml.safe_load(f)
        self.intent_matcher = make_joint_matcher(
            base_matcher=dialogic.nlu.matchers.TFIDFMatcher(),
            intents=intents,
        )
        self.faq_dm = dialogic.dialog_manager.faq.FAQDialogManager(
            faq_file, matcher='cosine',
        )
        self.faq_dm.matcher.threshold = 0.8

    def respond(self, ctx: dialogic.dialog.Context):
        uo = ctx.user_object or {}

        logger.debug(f'starting user object: {len(uo.get("found_skills") or [])} skills,'
                     f'page {uo.get("found_skills_page")} ')

        text = dialogic.nlu.basic_nlu.fast_normalize(ctx.message_text)
        intents = self.intent_matcher.aggregate_scores(text)
        faq_response = self.faq_dm.try_to_respond(ctx)

        result_number = nlu.get_exact_details_skill(text)

        prev_results = None
        if uo.get('found_skills'):
            prev_results = [
                self.engine.docs[doc_id]
                for doc_id in uo['found_skills']
                if doc_id in self.engine.docs
            ]

        if not ctx.message_text or ctx.message_text == '/start':
            resp_text = 'Привет! Это навык "Искатель навыков" для поиска других навыков. ' \
                        'Можете спросить меня, например, "Какой навык рассказывает про костный мозг?" ' \
                        'Чтобы выйти, скажите "Алиса, хватит"'
            return dialogic.dialog.Response(resp_text)
        elif ctx.message_text == 'ping' and ctx.session_is_new():
            return dialogic.dialog.Response('pong!')
        elif dialogic.basic_nlu.like_help(ctx.message_text):
            resp_text = 'Вы в навыке "Искатель навыков" для поиска других навыков. ' \
                        'Можете спросить меня, например, "Какой навык рассказывает про костный мозг?" ' \
                        'Чтобы выйти, скажите "Алиса, хватит"'
            return dialogic.dialog.Response(resp_text, suggests=['Хватит'])
        elif dialogic.basic_nlu.like_exit(ctx.message_text) or 'exit_skill' in intents:
            resp_text = 'Всего доброго! Чтобы вернуться в навык, ' \
                        'скажите "Алиса, включи навык "Искатель навыков".'
            return dialogic.dialog.Response(resp_text, commands=[dialogic.COMMANDS.EXIT])
        elif 'run_skill' in intents:
            resp_text = random.choice([
                'Чтобы запускать другие навыки, вам нужно сначала выйти из этого.',
                'Чтобы запустить другой навык, сначала покиньте этот.',
                'Для запуска других навыков вам нужно вернуться к Алисе. Скажите "хватит", чтобы выйти.',
            ])
            return dialogic.dialog.Response(resp_text, suggests=['Хватит'])
        elif faq_response:
            faq_response.updated_user_object = uo
            return faq_response
        elif 'next_skills' in intents and prev_results and 'found_skills_page' in uo:
            uo['found_skills_page'] += 1
            resp_text, links, suggests = format_serp(prev_results, page=uo['found_skills_page'])
            response = dialogic.dialog.Response(resp_text, links=links, user_object=uo, suggests=suggests)
            return response
        elif 'prev_skills' in intents and prev_results and 'found_skills_page' in uo:
            uo['found_skills_page'] -= 1
            resp_text, links, suggests = format_serp(prev_results, page=uo['found_skills_page'])
            response = dialogic.dialog.Response(resp_text, links=links, user_object=uo, suggests=suggests)
            return response
        elif result_number is not None and prev_results and 'found_skills_page' in uo:
            links = []
            if 1 <= result_number <= len(prev_results):
                doc: dict = prev_results[result_number-1]
                resp_text = 'Навык "{}".\n{}'.format(
                    doc['name'], doc['description'],
                )
                resp_text = nlg.clip_text(resp_text, 1000)
                links.append({
                    'title': 'Запустить навык',
                    'hide': False,
                    'url': 'https://alice.ya.ru/s/{}'.format(doc['id']),
                })
            else:
                resp_text = 'Навыка с таким номером я не нашла.'
            suggests = ['к списку']
            return dialogic.dialog.Response(resp_text, user_object=uo, suggests=suggests, links=links)
        elif 'go_to_list' in intents and prev_results and 'found_skills_page' in uo:
            resp_text, links, suggests = format_serp(prev_results, page=uo['found_skills_page'])
            return dialogic.dialog.Response(resp_text, links=links, user_object=uo, suggests=suggests)

        search_text = nlu.get_search_text(ctx.message_text)
        results = self.engine.find(search_text)
        if not results:
            resp_text = 'Простите, ничего не нашла по запросу "{}".'.format(search_text)
            return dialogic.dialog.Response(resp_text)
        uo['found_skills'] = [doc['id'] for doc in results]
        uo['found_skills_page'] = 0
        resp_text, links, suggests = format_serp(results)
        response = dialogic.dialog.Response(resp_text, links=links, user_object=uo, suggests=suggests)
        return response


def format_serp(results, page=0, page_size=3):
    first = page * page_size
    if first < 0:
        first += len(results)
    if first >= len(results):
        first = first % len(results)
    last = first + page_size
    resp_text = 'Нашла {} навыков'.format(len(results))
    if last <= page_size:
        resp_text = resp_text + ':'
    elif first == 0:
        resp_text = resp_text + ', вот первые три:'
    else:
        resp_text = resp_text + ', вот следующие три:'
    links = []
    suggests = []
    for i, doc in enumerate(results[first: last]):
        resp_text = resp_text + '\n {}: {};'.format(
            first + i + 1,
            nlg.skill_title(doc),
        )
        suggests.append(str(first + i + 1))
        links.append({
            'title': doc['name'],
            'hide': False,
            'url': 'https://alice.ya.ru/s/{}'.format(doc['id']),
        })
    if last + 1 < len(results):
        suggests.append('дальше')
    if first > 0:
        suggests.append('назад')
    return resp_text, links, suggests


def make_joint_matcher(base_matcher: dialogic.nlu.matchers.BaseMatcher, intents, threshold=0.8):
    # todo: integrate it to dialogic
    labels = []
    texts = []
    re_labels = []
    re_texts = []
    for intent_name, intent in intents.items():
        if 'regexp' in intent:
            exps = intent['regexp']
            if not isinstance(exps, list):
                exps = [exps]
            for exp in exps:
                re_labels.append(intent_name)
                re_texts.append(exp)
        if 'examples' in intent:
            for ex in intent['examples']:
                labels.append(intent_name)
                texts.append(ex)
    base_matcher.fit(texts, labels)
    re_matcher = dialogic.nlu.matchers.RegexMatcher()
    re_matcher.fit(re_texts, re_labels)
    return dialogic.nlu.matchers.MaxMatcher([base_matcher, re_matcher], threshold=threshold)
