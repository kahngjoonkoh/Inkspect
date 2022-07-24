import nltk, spacy
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer


def analyze(rs):
    rs = sorted(rs, key=lambda d: d['resID'])
    for r in rs:
        res_pos = r['response']


def get_pos(response):
    tokens = nltk.word_tokenize(response)

    return nltk.pos_tag(tokens)


nlp = spacy.load('en_core_web_md')


def word_similarity(words):
    tokens = nlp(words)

    # for token in tokens:
    #     # Printing the following attributes of each token.
    #     # text: the word string, has_vector: if it contains
    #     # a vector representation in the model,
    #     # vector_norm: the algebraic norm of the vector,
    #     # is_oov: if the word is out of vocabulary.
    #     print(token.text, token.has_vector, token.vector_norm, token.is_oov)

    token1, token2 = tokens[0], tokens[1]

    print(token1.similarity(token2))


def get_path_similarity():
    print("Enter two space-separated words")
    words = input()
    word_similarity(words)
    words = words.split()
    # tokens = nlp(words)

    n = wn.synsets(words[0])
    g = wn.synsets(words[1])
    print(max(i.path_similarity(n[0]) for i in g), max(i.path_similarity(g[0]) for i in n))
    print(max(i.wup_similarity(n[0]) for i in g),
          max(i.wup_similarity(g[0]) for i in n))


def sentiment_analysis():
    words = input()

    print(sia.polarity_scores(words))


sia = SentimentIntensityAnalyzer()


# Part-Of-Speech Tagging
def tag_POS(s):
    tokens = nltk.word_tokenize(s)

    return nltk.pos_tag(tokens)


def get_keywords(pos):
    stop_words = set(stopwords.words('english'))
    new_list = []

    for annotation in pos:
        if annotation[0] in stop_words:
            pass
        else:
            new_list.append(annotation)
    return new_list


def detect_movement(kw):
    new_list = []
    for annotation in kw:
        if annotation[1] in ['VBG', 'VBD', 'JJ']:
            new_list.append(annotation)
    return new_list


# Detects whether the movement is active or passive.
def detect_AP(movement):
    PASSIVE_THRESHOLD = 0.3
    ACTIVE_THRESHOLD = 0.3
    active = False
    passive = False
    active_word_tokens = nlp("arguing yelling glaring reaching")
    passive_word_tokens = nlp("talking whispering looking standing setting bending sighing")

    for annotation in kw:
        token = nlp(annotation[0])
        max(active_word.similarity(token) for active_word in active_word_tokens)


# Morbid Content
def check_MOR(response, inquiry):
    MOR_THRESHOLD = -0.4
    if sia.polarity_scores(response)['compound'] < MOR_THRESHOLD:
        return True
    elif sia.polarity_scores(inquiry)['compound'] < MOR_THRESHOLD:
        return True
    else:
        return False


if __name__ == "__main__":
    # analyze([{"resId": 1, "id": 1, "no": 1, "response": "bat", "loc": "D3", "verbatim": "The colour is red."}])
    # print(get_pos("The object I see is kinda sprinting."))
    # print(get_pos("I see a running person."))
    # print(get_pos("A running person."))
    # print(get_pos("The person is as if he is jogging."))
    # print(get_pos("Swimming in the ocean has been Sharon's passion since she was five years old."))
    # VBG -> determinant.
    kw = get_keywords(tag_POS("The rat is depressed. It seems like a running bear."))
    print(kw)
    print(detect_movement(kw))
    for i in range(10):
        get_path_similarity()
    # for i in range(10):
    #     sentiment_analysis()