from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Catalog, Base, CatalogItem

engine = create_engine('sqlite:///catalogitem.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()



#Menu for UrbanBurger
category1 = Catalog(name = "Food")

session.add(category1)
session.commit()


catalogItem1 = CatalogItem(name = "French Fries", description = "with garlic and parmesan", catalog = category1)

session.add(catalogItem1)
session.commit()

catalogItem2 = CatalogItem(name = "Chicken Burger", description = "Juicy grilled chicken patty with tomato mayo and lettuce", catalog = category1)

session.add(catalogItem2)
session.commit()

catalogItem3 = CatalogItem(name = "Chocolate Cake", description = "fresh baked and served with ice cream", catalog = category1)

session.add(catalogItem3)
session.commit()



#Menu for Super Stir Fry
category2 = Catalog(name = "Sports")

session.add(category2)
session.commit()


categoryItem1 = CatalogItem(name = "Football", description = "Boring", catalog = category2)

session.add(categoryItem1)
session.commit()

categoryItem2 = CatalogItem(name = "Baseball", description = " Boring++", catalog= category2)

session.add(categoryItem2)
session.commit()
