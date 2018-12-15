from orator.migrations import Migration

class CreateItemsTable(Migration):

    def up(self):
        """
        Run the migrations.
        """
        with self.schema.create('items') as table:
            table.increments('id')
            table.string('title').unique()
            table.string('image').nullable().default('images/book.png')
            table.text('description')
            table.integer('category_id').unsigned()
            table.integer('user_id').unsigned()

    def down(self):
        """
        Revert the migrations.
        """
        self.schema.drop('items')
