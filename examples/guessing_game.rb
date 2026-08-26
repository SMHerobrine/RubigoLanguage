function main():
    print("Hi! Welcome to the Number Guessing Game.\nYou have 7 chances to guess the number. Let's start!")
    var low_bound: Int = input("Enter the Lower Bound: ")
    var high_bound: Int = input("Enter the Upper Bound: ")

    print("\nYou have 7 chances to guess the number between {low_bound} and {high_bound}. Let's start!")

    var number: random.int(low_bound, high_bound)
    # Total allowed chances
    var chance: Int = 7
    # Guess Counter
    var change guess_counter: Int = 0

    while guess_counter < chance:
        guess_counter += 1
        var guess: Int = input("Enter your Guess: ")

        if guess == number:
            print("Correct! The number is {number}. You guessed it in {guess_counter} attempts.")
            break
        elif guess_counter >= chance and guess != number:
            print("Sorry! The number was {number}. Better luck next time.")
        elif guess > number:
            print("Too High! Try a lower number.")
        elif guess < number:
            print("Too Low! Try a higher number.")
end
