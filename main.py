"""
word list is from https://gist.github.com/dracos/dd0668f281e685bad51479e5acaadb93
word frequencies are from https://tmh.conlang.org/word-frequency/ and https://www.kaggle.com/datasets/rtatman/english-word-frequency
- i split up each list very roughly into six frequency levels based on how often i saw unusual-looking words in different ranges of frequency rating numberes, and then averaged the results from the two lists
i used a second, smaller wordlist to sanity-check some very rare words that the script was guessing too often: https://www-cs-faculty.stanford.edu/~knuth/sgb-words.txt
- i checked for any word that had been assigned a high frequency but was not on this second list, and manually decreased the frequency rating of most of them
TODO
- try optimizing check_word() so we can do bigger sublists
  - actually i don't think i can optimize it more
- sometimes the script guesses the right word faster in hardmode, which i think shouldn't be the case
  - e.g. usually gets "puppy" in 6 guesses on nonhardmode but only 4-5 on hardmode
- maybe guesses should prioritize distinguishing between common words (and not worry as much about rare ones)
"""
import random


class WordleSolver:
    def __init__(self, wordlist):
        """Constructor
        Args:
            wordlist(list(list(str))): list of all valid words
        """
        # ADJUSTABLE PARAMS
        # multiplier for how much rare words are penalized. lower this to allow more unusual guesses
        # 1 = no penalty; 2 = occasionally odd words but usually fine; 3 = worked well but probably unnecessarily high
        self.highest_penalty = 2.5
        # maximum number of comparisons for searching for the next guess to make. higher value gives more accuracy but takes longer time
        # i tested values of 1mil (2 sec), 4mil (6 sec), and 10mil (17 sec), and they all seemed to perform about the same, so higher value doesn't seem to make much difference
        # 100k is definitely a degradation in performance (but lightning fast)
        self.max_comparisons = 1000000

        self.wordlist, self.freqs = zip(*wordlist)
        self.wordlist_filtered = self.wordlist[:]
        self.turn = 0
        self.hardmode = None
        self.penalty_dict = self.get_freq_penalty_dict()

    def get_freq_penalty_dict(self):
        """Read the word frequency file and store a dict of penalties for each word, which we'll use to help avoid guessing unrecognizable words
        Returns:
            dict(str:float)
        """
        d = {}
        # rarer words are going to get higher penalties against being chosen
        penalties = [3, 2, 1.5, 1.25, 1.1, 1]
        # adjust penalties based on chosen max penalty
        penalties = [(self.highest_penalty-1)*(p-1)/2 + 1 for p in penalties]
        # the frequency list gives each word's relative frequency ranked from 1 (rare) to 6 (common)
        for w,f in zip(self.wordlist, self.freqs):
            d[w] = penalties[int(f)-1]
        return d

    def check_word(self, target, guess):
        """Check the guess word against the target word
        Args:
            target(str): target word
            guess(str): guessed word
        Returns:
            str, e.g. "XXGYX" indicating the result of the guess
        """
        target = [t for t in target]
        guess = [g for g in guess]
        result = ['X'] * 5
        # check for greens
        for i,(t,g) in enumerate(zip(target,guess)):
            if t == g:
                result[i] = 'G'
                target[i] = '-'
                guess[i] = '-'
        # check for yellows
        for i,g in enumerate(guess):
            if g != '-' and g in target:
                j = target.index(g)
                result[i] = 'Y'
                target[j] = '-'
                guess[i] = '-'
        return ''.join(result)

    def filter_wordlist(self, guess, result):
        """Filter wordlist based on the result of a guess
        Args:
            guess(str): guess that was made
            result(str): result of that guess, e.g. "XXGYX"
        """
        green = []
        yellow = []
        # first filter by green letters by dropping words without that letter in that spot
        for i, (g, r) in enumerate(zip(guess, result)):
            if r == 'G':
                self.wordlist_filtered = [word for word in self.wordlist_filtered if word[i] == g]
                green.append(g)
        # next filter yellow letters by dropping words with that letter in that spot, and dropping words with fewer of that letter than there are greens and yellows of it
        for i, (g, r) in enumerate(zip(guess, result)):
            if r == 'Y':
                self.wordlist_filtered = [word for word in self.wordlist_filtered if word[i] != g]
                self.wordlist_filtered = [word for word in self.wordlist_filtered if word.count(g) >= 1 + green.count(g) + yellow.count(g)]
                yellow.append(g)
        # next filter grey letters by dropping words with that letter in that spot, and dropping words with more of that letter than there are greens and yellows of it
        for i, (g, r) in enumerate(zip(guess, result)):
            if r == 'X':
                self.wordlist_filtered = [word for word in self.wordlist_filtered if word[i] != g]
                self.wordlist_filtered = [word for word in self.wordlist_filtered if word.count(g) == green.count(g) + yellow.count(g)]

    def get_best_guess(self):
        """Find the best next word to guess
        Returns:
            str: the word to guess
        """
        # Strategy:
        # - First, make a sublist of all words in the lexicon that haven't been eliminated already. If the list is small, just use the whole list
        # - Use check_word() for each word in the lexicon against each word in the sublist to get a color result
        #   - If hardmode, use the non-eliminated lexicon instead of the full lexicon
        # - For each *unique* color result found in this manner, count how many word pairings got that result
        # - Return the word that has words distributed among the color results most usefully, so that the most words are eliminated regardless of the result
        # Note: the sublist length is capped in such a way as to do no more than 4 million comparisons, which appears to take around 5-6 seconds. This is an arbitrary limit to keep this function from running extremely long

        # if there are no possibilities left, the player either gave bad info or chose a target word not in the wordlist
        if not self.wordlist_filtered:
            return None
        # if there are only 1 or 2 possibilities left, we should just guess the more common one of them. (without this check, non-hardmode's algorithm will keep trying to make narrowing-down guesses and never guess the right answer)
        if len(self.wordlist_filtered) == 1:
            return self.wordlist_filtered[0]
        elif len(self.wordlist_filtered) == 2:
            return self.wordlist_filtered[1] if self.penalty_dict[self.wordlist_filtered[1]] < self.penalty_dict[self.wordlist_filtered[0]] else self.wordlist_filtered[0]
        # if there are relatively few possibilities left and all but one are much less common, just guess the common word
        elif len(self.wordlist_filtered) <= 6:
            pens = [(w,self.penalty_dict[w]) for w in self.wordlist_filtered]
            pens.sort(key=lambda x:x[1])
            if pens[0][1] <= pens[1][1]-(self.highest_penalty-1)/4:
                return pens[0][0]

        if self.hardmode:
            wordlist = self.wordlist_filtered
        else:
            wordlist = self.wordlist
        compares_per_word = min(self.max_comparisons//len(wordlist), len(wordlist))
        if compares_per_word >= len(self.wordlist_filtered):
            sublist = self.wordlist_filtered
        else:
            sublist = random.sample(self.wordlist_filtered, compares_per_word)
        # result_dict will be formatted as {word:{result:count}}, i.e. with each word paired with a dict of unique results, and each of those results with a list of counts of how many words gave that result
        result_dict = {}
        for guess in wordlist:
            for target in sublist:
                result = self.check_word(target, guess)
                if guess not in result_dict:
                    result_dict[guess] = {}
                if result not in result_dict[guess]:
                    result_dict[guess][result] = 1
                else:
                    result_dict[guess][result] += 1
        # simplify to {word:max(counts)} since that's all we actually care about
        result_dict = {w:max([c for c in result_dict[w].values()]) for w in result_dict}
        # apply penalty weights to make less common words less likely to get chosen
        result_dict = {w:result_dict[w]*self.penalty_dict[w] for w in result_dict}
        # choose the word with the lowest (penalized) max count. if we used the raw max count, this means it would be impossible to have more than that number of possibilities left after we guess that word
        lowest_max_word = None
        lowest_max = 999999999999
        for w in result_dict:
            if result_dict[w] < lowest_max:
                lowest_max_word = w
                lowest_max = result_dict[w]
        return lowest_max_word

    def ordinal(self, num):
        """Get ordinal
        Args:
            num(str): number string to add ordinal to
        Returns:
            str
        """
        if str(num)[-1] == '1':
            return str(num)+'st'
        elif str(num)[-1] == '2':
            return str(num)+'nd'
        elif str(num)[-1] == '3':
            return str(num)+'rd'
        else:
            return str(num)+'th'

    def validate_color_string(self, s):
        """Validate color string
        Args:
            s(str): color string to validate
        """
        if len(s) != 5:
            return False
        if any([l not in 'GXY' for l in s]):
            return False
        return True

    def play(self, target=None):
        """Play the game
        Args:
            target(str/None): the target word, if playing automatically, or None if playing manually
        """
        valid = False
        while not valid:
            hardmode = input('Play in hardmode? (Y/N): ').upper()
            valid = hardmode in 'YN'
        self.hardmode = hardmode=='Y'

        print()
        while True:
            self.turn += 1
            guess = self.get_best_guess()
            if guess is None:
                print('NO KNOWN WORDS LEFT!')
                return None
            print('My', self.ordinal(self.turn), 'guess is:', guess.upper())
            valid = False
            while not valid:
                if target is None:
                    result = input('Tell me the color result (e.g. "XXGYX"): ').upper()
                else:
                    result = self.check_word(target, guess)
                    print('Tell me the color result (e.g. "XXGYX"):',result)
                valid = self.validate_color_string(result)
            if result == 'GGGGG':
                if self.turn <= 6:
                    print('I WIN!')
                return self.turn
            elif self.turn == 6:
                print('I LOSE!')
            self.filter_wordlist(guess, result)
            print('REM:',len(self.wordlist_filtered))
            if len(self.wordlist_filtered) <= 30:
                print(self.wordlist_filtered)
            print()


if __name__ == '__main__':
    f = open('wordfreqsfinal.txt')
    lines = f.read().splitlines()
    lines = [line.split() for line in lines]
    lines = [(w,int(n)) for w,n in lines]
    solver = WordleSolver(lines)
    score = solver.play()
    print('Solved in',score,'turns')
