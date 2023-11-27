import time

from deepllm.interactors import Agent
from deepllm.api import *


def clean_sent(sent):
    sent = sent.strip().replace(' .', '.').replace('..', '')
    sent = sent.replace(' -', '-').replace("'", "_")
    sent = " ".join(sent.split())
    if not sent.endswith('.'): sent = sent + "."
    return sent


def clean_quest(x0, sent, context):
    # print('!!! CLEANING:',x)
    x = x0.strip()

    assert x, ("Empty!!!!", (sent, context))

    if x[0] in ("'", '"'): x = x[1:]
    if x[-1] in ("'", '"'): x = x[0:-1]

    assert x and x[0:3] in ['Q: ', 'A: '], x0
    return x


def to_quests(agent, question, context, short_size=4, k=3):
    agent.set_pattern(None)
    p = f"""
    With the context "{context}" in mind,
    generate {k} different answers to "{question}".
    Prefix each answer with "A:", but do NOT number them as in "A1: or 1. ".
    After returning each answer, suggest a salient follow-up question to your answer, prefixed with "Q:" . 
    """
    prompt = " ".join(p.split())

    answer = agent.ask(prompt)

    # print('PROMPT:',prompt)
    # print('RETURN:',answer)
    # print()

    return answer


def quest2quests(agent, quest, context, k=3):
    t1 = time.time()

    quests_ = to_quests(agent, quest, context, k=k)
    quests0 = quests_.replace('\n\n', '\n').split('\n')
    quests = [clean_quest(q, quest, context) for q in quests0]
    # print('LENS:', len(quests0), len(quests))
    assert len(quests) % 2 == 0, (len(quests0), len(quests), quests0)

    pairs = []
    for j, x in enumerate(quests):

        # print('    ' + x)
        p = x[0:3]
        assert p in ['Q: ', 'A: ']
        x = x[3:]
        if j % 2 == 0:
            assert p == "A: ", (p, x)
            a = x  # answers

            q = quests[j + 1]
            p_ = q[0:3]
            q = q[3:]  # quest: previous position
            assert p_ == "Q: ", (p_, q)
            pair = (a, q)
            pairs.append(pair)

    t2 = time.time()
    print('TIME:', round(t2 - t1, 4))
    print('COSTS:', round(agent.dollar_cost(), 4))
    return pairs


def one_quest(agent, quest, context, trim_size=3):
    agent.set_initiator(quest)
    res = quest2quests(agent, quest, context, k=1)
    agent.trim_at(trim_size)
    agent.persist()
    a, q = res[0]
    return a, q


def make_agent():
    agent = Agent(name='QA_generator')
    agent.resume()
    return agent


def localize(local):
    if local:
        local_model()
    else:
        key = os.getenv("OPENAI_API_KEY")
        set_openai_api_key(key)
        # smarter_model()
        cheaper_model()


def recursor(initiator, trim_size=4, max_k=2, max_d=5):
    agent = make_agent()

    def generate(quest, d):
        pairs = quest2quests(agent, quest, initiator, k=max_k)
        agent.trim_at(trim_size)
        for a, q in pairs:
            if d >= max_d:
                yield (quest,a),
            else:
                for trace in generate(q, d + 1):
                    yield ((quest, a),) + trace

    for trace in generate(initiator, 0):
        agent.persist()
        show_mems(agent)
        yield trace


def show_mems(agent):
    print('SHORT_TERM_MEMORY SIZE:',
          len(agent.short_mem),
          'LONG_TERM_MEMORY SIZE:',
          len(agent.long_mem),
          'COSTS:', round(agent.dollar_cost(), 4))

def test_qa_maker(fresh=0, local=1):
    localize(local)
    agent = make_agent()
    agent.resume()
    initiator = "Why do some people think that we live in a simulation?"
    print('INITIATOR:', initiator)
    for thread in recursor(initiator):
        print('\nTHREAD:\n')
        for q, a in thread:
            print('Q:', q)
            print('A:', a)
            print()
        print()
        agent.persist()
    if fresh: agent.clear()
    print('SHORT_TERM_MEMORY SIZE:',
          len(agent.short_mem),
          'LONG_TERM_MEMORY SIZE:',
          len(agent.long_mem),
          'COSTS:', round(agent.dollar_cost(), 4))


def test_qa_maker1(fresh=0):
    agent = make_agent()
    agent.resume()
    # quest = "Why do some people think that We live in a simulation?"
    quest = "Why would introducing a planning element in the training of an LLM be a big step toward AGI?"
    print('QUEST0:', quest)
    for a, q in quest2quests(agent, quest, quest):
        print('A:', a)
        print('Q:', q)
        print()
    x = one_quest(agent, quest, 'think clearly')
    print('QA:', x)
    agent.persist()
    if fresh: agent.clear()


if __name__ == "__main__":
    test_qa_maker()