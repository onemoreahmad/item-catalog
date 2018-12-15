from orator.seeds import Seeder
from app import Category


class CategoriesTableSeeder(Seeder):

    def run(self):
        """
        Run the database seeds.
        """
        categories = [
            "Art",
            "Biography",
            "Business",
            "Children's",
            "Mystery",
            "Manga",
            "Science",
            "Self Help",
            "Spirituality",
            "Travel",
            "Thriller"
        ]

        for category in categories:
            Category.create(title=category)
