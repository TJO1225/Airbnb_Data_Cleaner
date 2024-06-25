"""empty message

Revision ID: dbb1b2088501
Revises: 
Create Date: 2024-06-25 03:44:35.273387+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dbb1b2088501'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('airbnb_reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_reviews', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('total_months', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('missing_months', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('avg_reviews_per_month', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('high_season_reviews', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('high_season', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('high_season_insights', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('bedroom_label', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('number_of_guests', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('url', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('location', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('stars', sa.Float(), nullable=True))
        batch_op.alter_column('review_text',
               existing_type=sa.VARCHAR(length=500),
               type_=sa.Text(),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('airbnb_reviews', schema=None) as batch_op:
        batch_op.alter_column('review_text',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=500),
               existing_nullable=True)
        batch_op.drop_column('stars')
        batch_op.drop_column('location')
        batch_op.drop_column('url')
        batch_op.drop_column('number_of_guests')
        batch_op.drop_column('bedroom_label')
        batch_op.drop_column('high_season_insights')
        batch_op.drop_column('high_season')
        batch_op.drop_column('high_season_reviews')
        batch_op.drop_column('avg_reviews_per_month')
        batch_op.drop_column('missing_months')
        batch_op.drop_column('total_months')
        batch_op.drop_column('total_reviews')

    # ### end Alembic commands ###
