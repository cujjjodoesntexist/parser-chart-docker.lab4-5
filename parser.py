import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from config import db_url, log_path

Base = declarative_base()


class Recipe(Base):
    __tablename__ = 'recipes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    cal = Column(String, nullable=False)
    time = Column(String, nullable=False)
    ingredients = relationship('Ingredient', secondary='connection_table')


class Ingredient(Base):
    __tablename__ = 'ingredients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


class ConnectionTable(Base):
    __tablename__ = 'connection_table'
    recipe_id = Column(Integer, ForeignKey('recipes.id'), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey('ingredients.id'), primary_key=True)

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_request(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response


def session_():
    clarifying_links = []
    page = 0
    while len(clarifying_links) < 1000:
        page += 1
        try:
            url = f'https://eda.ru/recepty?page={page}'
            response = get_request(url)
            soup = BeautifulSoup(response.text, 'lxml')
            for recipe_list in soup.find_all('div', class_='emotion-1j5xcrd'):
                for recipe_link in recipe_list.find_all('a', href=True):
                    full_link = 'https://eda.ru' + recipe_link['href']
                    clarifying_links.append(full_link)
                    if len(clarifying_links) >= 1000:
                        break
            logging.info(f"Страница {page} обработана. Общее количество уточняющих ссылок собрано: {len(clarifying_links)}")
        except Exception as e:
            logging.error(f"Ошибка обработки страницы {page}: {e}")
            break

    for link in clarifying_links:
        try:
            response = get_request(link)
            soup = BeautifulSoup(response.text, 'lxml')

            name = soup.find('h1', class_='emotion-gl52ge').get_text().replace('\xa0', ' ')
            calories = soup.find('span', itemprop='calories').get_text()
            cook_time = soup.find('span', itemprop='cookTime').get_text()

            ingredients = []
            for ingredient in soup.find_all('div', class_='emotion-1oyy8lz'):
                ingredients.append(ingredient.find('span', itemprop='recipeIngredient').get_text().replace('\xa0', ' '))

            recipe = Recipe(name=name, cal=calories, time=cook_time)
            session.add(recipe)
            session.commit()
            logging.info(f"Рецепт '{name}' добавлен в базу данных.")

            for ing_name in ingredients:
                ingredient = session.query(Ingredient).filter_by(name=ing_name).first()
                if not ingredient:
                    ingredient = Ingredient(name=ing_name)
                    session.add(ingredient)
                    session.commit()

                connection = ConnectionTable(recipe_id=recipe.id, ingredient_id=ingredient.id)
                session.add(connection)

            session.commit()
        except IntegrityError as ie:
            session.rollback()
            logging.warning(f"Ошибка целостности: {ie}. Ссылка {link} пропускается.")
        except Exception as e:
            session.rollback()
            logging.error(f"Не удалось обработать ссылку {link}: {e}")

    logging.info("Сбор данных завершен.")

if __name__ == "__main__":
    logging.basicConfig(filename=log_path, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    try:
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        session_()
    except Exception as e:
        logging.error(f"Ошибка при запуске {e}")
