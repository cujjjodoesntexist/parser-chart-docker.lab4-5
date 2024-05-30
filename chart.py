from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import matplotlib.pyplot as plt
from collections import Counter
import re
from parser import Recipe, Ingredient, ConnectionTable, Base
from config import db_url


def analyze():
    recipes = session.query(Recipe).all()
    connections = session.query(ConnectionTable).all()

    ingredient_counter = Counter()
    for conn in connections:
        ingredient = session.query(Ingredient).filter(Ingredient.id == conn.ingredient_id).one()
        ingredient_counter[ingredient.name] += 1

    most_common_ingredients = ingredient_counter.most_common(10)
    print("Самые часто используемые ингредиенты:")
    for ingredient, count in most_common_ingredients:
        print(f"{ingredient}: {count}")


    def convert_to_minutes(time_str):
        main_time = time_str.split('+')[0].strip()
        total_minutes = 0

        hour_pattern = re.compile(r'(\d+)\s*час[а-я]*')
        minute_pattern = re.compile(r'(\d+)\s*минут[а-я]*')

        hours_match = hour_pattern.search(main_time)
        minutes_match = minute_pattern.search(main_time)

        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60

        if minutes_match:
            total_minutes += int(minutes_match.group(1))
        return total_minutes

    calories = []
    time = []

    for recipe in recipes:
        calories.append(int(recipe.cal))
        time.append(convert_to_minutes(recipe.time))

    # Plot the data
    plt.figure(figsize=(7, 5))
    plt.scatter(time, calories, alpha=0.5, color='r')
    plt.title('Зависимость калорийности от времени приготовления')
    plt.xlabel('Время приготовления (минуты)')
    plt.ylabel('Калории (ккал)')
    plt.grid(True)
    plt.show()

    session.close()


if __name__ == '__main__':
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    analyze()
