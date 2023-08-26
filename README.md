# wordle-solver

Solves a Wordle intelligently. The solver will make guesses, and you will tell it what letters in its guess were correct. The solver will attempt to find the correct word in as few guesses as possible

Choose from hardmode (solver only guesses words that are still possible based on its previous guesses) or non-hardmode (solver can always guess any word). Then tell the solver the colors for its guesses with a 5-letter string like `ygxxg`
- Use `g` for a green letter (a letter that is exactly correct)
- Use `y` for a yellow letter (a letter that is somewhere in the word but not where the solver guessed it)
- Use `x` for a grey letter (a letter that is not in the word)
