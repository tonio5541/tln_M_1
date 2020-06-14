import json

import requests as req
from simplenlg import framework as Framework
from simplenlg import lexicon as Lexicon
from simplenlg import realiser as Realiser
from simplenlg import phrasespec as PhraseSpec
from simplenlg import features as Features, Tense, Feature, Person

from googletrans import Translator

translator = Translator()
lexicon = Lexicon.Lexicon().getDefaultLexicon()
nlgFactory = Framework.NLGFactory(lexicon)
realiser = Realiser.Realiser(lexicon)


class Frase:
    def __init__(self, p):
        self.periodo = p
        self.paroleIT = []
        self.periodoEN = ""
        self.albero = None


# Inzio metodi per Albero
class Nodo:
    def __init__(self, p, t, f):
        self.dato = p
        self.features = f
        self.tipoNodo = t
        self.figli = []


def print_albero(root):
    print("parola: " + root.dato + " tipo: " + root.tipoNodo + " features: ")
    print(root.features)
    for f in root.figli:
        print_albero(f)


def get_albero(js, token, root):
    for j in js:
        if j['governorGloss'] == root.dato:
            root.figli.append(Nodo(j['dependentGloss'], j['dep'], take_token(j['dependentGloss'], token)['features']))

    for f in root.figli:
        get_albero(js, token, f)
    return root


def take_token(word, token):
    for t in token:
        if t['originalText'] == word:
            return t


# Fine Metodi per albero

# Inizio metodi costruzione frase
def set_feature(v, feature, b):
    if b:
        v.setFeature(Feature.PERFECT, True)
    if feature['Tense'][0] == 'Pres':
        v.setFeature(Feature.TENSE, Tense.PRESENT)
    elif feature['Tense'][0] == 'Past':
        v.setFeature(Feature.TENSE, Tense.PAST)

    if feature['Tense'][0] == 3:
        v.setFeature(Feature.PERSON, Person.THIRD)
    return v


def metodo(nodo, clause, i):
    global translator, nlgFactory
    verb_bool = False
    noun_bool = False
    prep_bool = False

    # Precontrolli sul padre nel caso fosse un NominalModifier o Dircet Object
    if nodo.tipoNodo == 'nmod':
        noun_bool = True
        n = nlgFactory.createNounPhrase()
        n.setNoun(translator.translate(nodo.dato, src='it', dest='en').text)
    if nodo.tipoNodo == 'dobj':
        noun_bool = True
        n = nlgFactory.createNounPhrase()
        n.setNoun(translator.translate(nodo.dato, src='it', dest='en').text)

    # Controlli sui figli in maniera diretta, ove possibile alucni rapporti di dipendenza tra padre e figlio vengono
    # gestiti in un unico giro di ricorsione
    for f in nodo.figli:
        if f.tipoNodo == 'nsubj':
            verb_bool = True
            v = nlgFactory.createVerbPhrase()
            v.setVerb(translator.translate(nodo.dato, src='it', dest='en').text)
            v = set_feature(v, nodo.features, False)
            clause.setSubject(translator.translate(f.dato, src='it', dest='en').text)
        if f.tipoNodo == 'aux':
            verb_bool = True
            v = nlgFactory.createVerbPhrase()
            v.setVerb(translator.translate(nodo.dato, src='it', dest='en').text)
            v = set_feature(v, f.features, True)
        if f.tipoNodo == 'auxpass':
            v.setFeature(Feature.PASSIVE, True)
        if f.tipoNodo == 'cop':
            verb_bool = True
            v = nlgFactory.createVerbPhrase()
            v.setVerb(translator.translate(f.dato, src='it', dest='en').text)
            v = set_feature(v, f.features, False)
        if f.tipoNodo == 'advmod' and verb_bool:
            # translator.translate("via", src='it', dest='en').extra_data
            v.setVerb(translator.translate(nodo.dato + " " + f.dato, src='it', dest='en').text)
        if f.tipoNodo == 'det' or f.tipoNodo == 'det:poss':
            if noun_bool:
                n.setDeterminer(translator.translate(f.dato, src='it', dest='en').text)
            else:
                noun_bool = True
                n = nlgFactory.createNounPhrase()
                n.setNoun(translator.translate(nodo.dato, src='it', dest='en').text)
                n.setDeterminer(translator.translate(f.dato, src='it', dest='en').extra_data['all-translations'][0][2][0][0])
        if f.tipoNodo == 'compound':
            n.addModifier(translator.translate(f.dato, src='it', dest='en').text)
        if f.tipoNodo == 'case':
            prep_bool = True
            p = nlgFactory.createPrepositionPhrase()
            p.setPreposition(translator.translate(f.dato, src='it', dest='en').text)
            p.addComplement(n)
        if f.tipoNodo == 'amod':
            if noun_bool:
                n.addPreModifier(translator.translate(f.dato, src='it', dest='en').text)
            elif prep_bool:
                p.addPreModifier(translator.translate(f.dato, src='it', dest='en').text)

    # Se alla fine del primo ciclo si sono create delle VerbPrhase NounPhrase o PrepositionalPhrase, esse devono essere
    # introdotte nella clausola (frase) di riferimento.
    if verb_bool:
        if noun_bool:
            v.setObject(n)
        clause.setVerbPhrase(v)
    if prep_bool:
        clause.addPostModifier(p)
    elif noun_bool:
        #if nodo.tipoNodo == 'nsubjpass':
        #    clause.setSubject(n)
        #else:
        clause.setObject(n)

    # Ciclo che permette la ricorsione, in alcuni casi viene inviato un riferimento diverso a quello che è il valore clausola
    # perchè logicamente la frase può essere scaglionata in piccoli elementi.
    for f in nodo.figli:
        if nodo.tipoNodo == 'nsubjpass' and f.tipoNodo == 'nmod':
            metodo(f, n, i)
        elif f.tipoNodo == 'nsubjpass':
            metodo(f, v, i)
        elif f.tipoNodo == 'dobj':
            metodo(f, v, i)
        elif f.tipoNodo == 'compound':
            metodo(f, n, i)
        else:
            metodo(f, clause, i)
    return clause

# Fine metodi costruzione frase

# PROGETTO Surdo.Antonio - Sanfilippo.Paolo
def main():
    global translator
    # Frasi da analizzare - Dichiarazione e creazione di array di oggetti di tipo Frase.
    frasi = [Frase({'text': 'Paolo ama Francesca'}), Frase({'text': 'è la spada laser di tuo padre'}), Frase({'text': 'Ha fatto una mossa leale'}),
             Frase({'text': 'Gli ultimi avanzi della vecchia Repubblica sono stati spazzati via'})]

    # Ciclo elaborazione
    # Creazione albero dipendenze - Tramite l'ausilio di Tint, dell'albero a dipendenze dato dalla frase in input.
    # Richiamo del metodo di analisi delle strutture dati create per ricostruire la frase in lingua straniere (da Italiano ad Inglese)

    i = 0
    for f in frasi:
        f.periodo['text'] = f.periodo['text'].lower()
        print('Frase ' + str(i) + ' originale :  ' + f.periodo['text'])
        url = 'http://localhost:8012/tint?'
        resp = req.get(url, params=f.periodo)
        root = Nodo(json.loads(resp.text)['sentences'][0]['basic-dependencies'][0]['dependentGloss'],
                    json.loads(resp.text)['sentences'][0]['basic-dependencies'][0]['dep'],
                    take_token(json.loads(resp.text)['sentences'][0]['basic-dependencies'][0]['dependentGloss'],
                               json.loads(resp.text)['sentences'][0]['tokens'])['features'])
        f.albero = get_albero(json.loads(resp.text)['sentences'][0]['basic-dependencies'],
                              json.loads(resp.text)['sentences'][0]['tokens'], root)
        # print_albero(f.albero) # Piccolo metodo per stampare l'albero usato in fase di progettazione.
        c = nlgFactory.createClause()
        c = metodo(f.albero, c, i)
        if (c.getVerbPhrase().getAllFeatures()['passive'] and c.getObject() is None) or (not(c.getVerbPhrase().getAllFeatures()['passive']) and c.getSubject() is None):
            if i == 1:
                c.setSubject('it')
            if i == 2:
                c.setSubject('he')
        s = nlgFactory.createSentence(c)
        frasi[i].periodoEN = realiser.realiseSentence(s)
        print('Frase ' + str(i) + ' tradotta :  ' + frasi[i].periodoEN)
        i = i + 1


main()
