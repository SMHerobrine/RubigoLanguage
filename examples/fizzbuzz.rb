#   Old Code
#

#   function main():
#        for number from 1 through 20:
#            if number % 15 == 0:
#                print "FizzBuzz"
#            otherwise if number % 3 == 0:
#                print "Fizz"
#            otherwise if number % 5 == 0:
#                print "Buzz"
#            otherwise:
#                print number
#            end
#        end
#    end


#
#   New Code
#

function main():
    for number from 1 through 20:
        if number % 15 == 0:
            print "FizzBuzz"
        else if number % 3 == 0:
            print "Fizz"
        else if number % 5 == 0:
            print "Buzz"
        else:
            print(number)
        end
    end
end