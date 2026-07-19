"""cobros informales

Revision ID: dd95ec70c1f3
Revises: 9d3f158bf521
Create Date: 2026-07-18 22:13:56.066543

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'dd95ec70c1f3'
down_revision = '9d3f158bf521'
branch_labels = None
depends_on = None


def upgrade():
    forma_pago_informal = sa.Enum('EFECTIVO', 'CHEQUE', 'TRANSFERENCIA', 'TARJETA', name='forma_pago_informal')
    forma_pago_informal.create(op.get_bind(), checkfirst=True)
    estado_cobro = sa.Enum('PENDIENTE', 'PAGADO', name='estado_cobro_informal')
    estado_cobro.create(op.get_bind(), checkfirst=True)

    op.create_table('cobros_informales',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cliente_id', sa.Integer(), nullable=False),
    sa.Column('concepto', sa.String(length=255), nullable=False),
    sa.Column('monto_total', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('saldo_pendiente', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('estado', estado_cobro, nullable=False),
    sa.Column('observaciones', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('cobros_informales', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cobros_informales_cliente_id'), ['cliente_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_cobros_informales_estado'), ['estado'], unique=False)

    op.create_table('abonos_cobro_informal',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cobro_informal_id', sa.Integer(), nullable=False),
    sa.Column('monto', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('forma_pago', forma_pago_informal, nullable=False),
    sa.Column('banco', sa.String(length=120), nullable=True),
    sa.Column('numero', sa.String(length=60), nullable=True),
    sa.Column('fecha', sa.DateTime(timezone=True), nullable=False),
    sa.Column('usuario', sa.String(length=120), nullable=False),
    sa.ForeignKeyConstraint(['cobro_informal_id'], ['cobros_informales.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('abonos_cobro_informal', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_abonos_cobro_informal_cobro_informal_id'), ['cobro_informal_id'], unique=False)

    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.drop_constraint('pagos_deuda_manual_id_fkey', type_='foreignkey')
        batch_op.drop_column('deuda_manual_id')

    with op.batch_alter_table('deudas_manuales', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_deudas_manuales_cliente_id'))
        batch_op.drop_index(batch_op.f('ix_deudas_manuales_estado'))

    op.drop_table('deudas_manuales')
    sa.Enum(name='estado_deuda_manual').drop(op.get_bind(), checkfirst=True)


def downgrade():
    sa.Enum(name='estado_deuda_manual').create(op.get_bind(), checkfirst=True)
    op.create_table('deudas_manuales',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('cliente_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('concepto', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('monto_total', sa.NUMERIC(precision=12, scale=2), autoincrement=False, nullable=False),
    sa.Column('saldo_pendiente', sa.NUMERIC(precision=12, scale=2), autoincrement=False, nullable=False),
    sa.Column('estado', postgresql.ENUM('PENDIENTE', 'PARCIAL', 'PAGADO', name='estado_deuda_manual'), autoincrement=False, nullable=False),
    sa.Column('observaciones', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('creado_en', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], name='deudas_manuales_cliente_id_fkey', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('deudas_manuales', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_deudas_manuales_estado'), ['estado'], unique=False)
        batch_op.create_index(batch_op.f('ix_deudas_manuales_cliente_id'), ['cliente_id'], unique=False)

    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deuda_manual_id', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.create_foreign_key('pagos_deuda_manual_id_fkey', 'deudas_manuales', ['deuda_manual_id'], ['id'], ondelete='SET NULL')

    with op.batch_alter_table('abonos_cobro_informal', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_abonos_cobro_informal_cobro_informal_id'))
    op.drop_table('abonos_cobro_informal')

    with op.batch_alter_table('cobros_informales', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cobros_informales_estado'))
        batch_op.drop_index(batch_op.f('ix_cobros_informales_cliente_id'))
    op.drop_table('cobros_informales')
    sa.Enum(name='forma_pago_informal').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='estado_cobro_informal').drop(op.get_bind(), checkfirst=True)
