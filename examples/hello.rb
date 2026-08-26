function greet(name: String):
    return String "Hello, {name}!"
end

function main():
    var languages: List(String) = ["Rubigo", "Rust"]

    for language in languages:
        print greet(language)
    end

    var change total: Integer = 0
    for number from 1 through 5:
        total = (total + number)
    end

    if total == 15:
        print("The total is {total}.")
    else
        print("Something unexpected happened.")
    end
end