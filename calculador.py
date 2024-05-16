def calculate_average(numbers):
    return sum(numbers) / len(numbers)

def main():
    averages = []
    with open('score.txt', 'r') as file:
        lines = file.readlines()
        for i in range(0, len(lines), 10):
            numbers = [int(line) for line in lines[i:i+10]]
            average = calculate_average(numbers)
            averages.append(average)
    
    print("Averages of each 10 lines: ", averages)
    print("Average of all averages: ", calculate_average(averages))
    print("Max average: ", max(averages))
    print("Min average: ", min(averages))
    print("Median average: ", sorted(averages)[len(averages)//2])

if __name__ == "__main__":
    main()
