"""deudas manuales y formas de pago

Revision ID: 9d3f158bf521
Revises: 7698191edb77
Create Date: 2026-07-18 21:49:12.017952

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d3f158bf521'
down_revision = '7698191edb77'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tipos enum primero
    tipo_cobro = sa.Enum('FACTURA', 'MANUAL', name='tipo_cobro')
    tipo_cobro.create(op.get_bind(), checkfirst=True)
    forma_pago = sa.Enum('EFECTIVO', 'CHEQUE', 'TRANSFERENCIA', 'TARJETA', name='forma_pago')
    forma_pago.create(op.get_bind(), checkfirst=True)

    op.create_table('deudas_manuales',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cliente_id', sa.Integer(), nullable=False),
    sa.Column('concepto', sa.String(length=255), nullable=False),
    sa.Column('monto_total', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('saldo_pendiente', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('estado', sa.Enum('PENDIENTE', 'PARCIAL', 'PAGADO', name='estado_deuda_manual', create_type=False), nullable=False),
    sa.Column('observaciones', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('deudas_manuales', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_deudas_manuales_cliente_id'), ['cliente_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_deudas_manuales_estado'), ['estado'], unique=False)

    with op.batch_alter_table('detalle_pagos', schema=None) as batch_op:
        batch_op.alter_column('factura_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tipo', tipo_cobro, nullable=False, server_default='FACTURA'))
        batch_op.add_column(sa.Column('forma_pago', forma_pago, nullable=False, server_default='EFECTIVO'))
        batch_op.add_column(sa.Column('banco', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('numero_cheque', sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column('fecha_cheque', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('nombre_titular', sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column('numero_referencia', sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column('fecha_transferencia', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('tipo_tarjeta', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('ultimos_4_digitos', sa.String(length=4), nullable=True))
        batch_op.add_column(sa.Column('numero_autorizacion', sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column('concepto_manual', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('deuda_manual_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_pagos_deuda_manual_id'), ['deuda_manual_id'], unique=False)
        batch_op.create_foreign_key(None, 'deudas_manuales', ['deuda_manual_id'], ['id'], ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_pagos_deuda_manual_id'))
        batch_op.drop_column('deuda_manual_id')
        batch_op.drop_column('concepto_manual')
        batch_op.drop_column('numero_autorizacion')
        batch_op.drop_column('ultimos_4_digitos')
        batch_op.drop_column('tipo_tarjeta')
        batch_op.drop_column('fecha_transferencia')
        batch_op.drop_column('numero_referencia')
        batch_op.drop_column('nombre_titular')
        batch_op.drop_column('fecha_cheque')
        batch_op.drop_column('numero_cheque')
        batch_op.drop_column('banco')
        batch_op.drop_column('forma_pago')
        batch_op.drop_column('tipo')

    with op.batch_alter_table('detalle_pagos', schema=None) as batch_op:
        batch_op.alter_column('factura_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    with op.batch_alter_table('deudas_manuales', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_deudas_manuales_estado'))
        batch_op.drop_index(batch_op.f('ix_deudas_manuales_cliente_id'))

    op.drop_table('deudas_manuales')
    sa.Enum(name='tipo_cobro').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='forma_pago').drop(op.get_bind(), checkfirst=True)
