"""
Script para sincronización de materiales y min/max desde la base remota
Ejecutar: python testRemote.py
"""
from app import app, db, Material, sync_materials_from_remote, sync_minmax_from_remote
import logging

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def force_sync():
    with app.app_context():
        print("\n" + "="*70)
        print("🔄 SINCRONIZACIÓN FORZADA DE MATERIALES")
        print("="*70)

        # Mostrar estado ANTES
        print("\n📊 ESTADO ANTES DE LA SINCRONIZACIÓN:")
        print("-" * 70)
        total_before = Material.query.count()
        print(f"Total de materiales locales: {total_before}")

        # Muestra de materiales actuales
        sample = Material.query.limit(5).all()
        print("\nMuestra de materiales actuales:")
        for mat in sample:
            print(f"  - {mat.code}: {mat.name} | Cat: '{mat.category}' | Unit: '{mat.unit}'")

        # Ejecutar sincronización
        print("\n🔄 Ejecutando sincronización...")
        print("-" * 70)
        result = sync_materials_from_remote()

        if result['success']:
            print(f"\n✅ SINCRONIZACIÓN EXITOSA")
            print(f"   📦 Nuevos materiales: {result['synced']}")
            print(f"   🔄 Materiales actualizados: {result['updated']}")
            print(f"   ⏭️  Materiales omitidos: {result.get('skipped', 0)}")
            print(f"   📊 Total procesados: {result['total']}")

            if result.get('errors'):
                print(f"\n⚠️  Errores encontrados: {len(result['errors'])}")
                for err in result['errors'][:5]:
                    print(f"   - {err}")
        else:
            print(f"\n❌ ERROR EN SINCRONIZACIÓN: {result.get('error')}")
            return

        # Mostrar estado DESPUÉS
        print("\n📊 ESTADO DESPUÉS DE LA SINCRONIZACIÓN:")
        print("-" * 70)
        total_after = Material.query.count()
        print(f"Total de materiales locales: {total_after}")
        print(f"Diferencia: +{total_after - total_before} materiales")

        # Muestra de materiales actualizados
        sample_after = Material.query.limit(10).all()
        print("\nMuestra de materiales después de sincronización:")
        for mat in sample_after:
            print(f"  - {mat.code}: {mat.name}")
            print(f"    Cat: '{mat.category}' | Unit: '{mat.unit}'")

        # Verificar variedad de unidades
        print("\n📏 VERIFICACIÓN DE UNIDADES:")
        print("-" * 70)
        from sqlalchemy import func
        units_query = db.session.query(
            Material.unit,
            func.count(Material.id).label('count')
        ).group_by(Material.unit).all()

        print("Distribución de unidades en materiales locales:")
        for unit, count in units_query:
            print(f"  - {unit}: {count} materiales")

        print("\n" + "="*70)
        print("✅ SINCRONIZACIÓN COMPLETADA")
        print("="*70 + "\n")


def sync_minmax():
    """Sincronizar valores mínimo y máximo"""
    with app.app_context():
        print("\n" + "="*70)
        print("🔄 SINCRONIZACIÓN DE MÍNIMOS Y MÁXIMOS")
        print("="*70)

        # Mostrar estado ANTES
        print("\n📊 ESTADO ANTES DE LA SINCRONIZACIÓN MIN/MAX:")
        print("-" * 70)

        from sqlalchemy import func

        # Contar materiales con min/max definidos
        with_minmax = Material.query.filter(
            (Material.min_stock > 0) | (Material.max_stock > 0)
        ).count()
        print(f"Materiales con min/max definidos: {with_minmax}")

        # Muestra de materiales
        sample = Material.query.limit(5).all()
        print("\nMuestra de materiales actuales:")
        for mat in sample:
            print(f"  - {mat.code}: {mat.name}")
            print(f"    Min: {mat.min_stock} | Max: {mat.max_stock}")

        # Ejecutar sincronización
        print("\n🔄 Ejecutando sincronización de min/max...")
        print("-" * 70)
        result = sync_minmax_from_remote()

        if result['success']:
            print(f"\n✅ SINCRONIZACIÓN MIN/MAX EXITOSA")
            print(f"   ✏️  Materiales actualizados: {result['updated']}")
            print(f"   ❓ No encontrados localmente: {result['not_found']}")
            print(f"   📊 Total procesados: {result['total']}")

            if result.get('errors'):
                print(f"\n⚠️  Errores encontrados: {len(result['errors'])}")
                for err in result['errors'][:5]:
                    print(f"   - {err}")
        else:
            print(f"\n❌ ERROR EN SINCRONIZACIÓN: {result.get('error')}")
            return

        # Mostrar estado DESPUÉS
        print("\n📊 ESTADO DESPUÉS DE LA SINCRONIZACIÓN MIN/MAX:")
        print("-" * 70)

        with_minmax_after = Material.query.filter(
            (Material.min_stock > 0) | (Material.max_stock > 0)
        ).count()
        print(f"Materiales con min/max definidos: {with_minmax_after}")
        print(f"Diferencia: +{with_minmax_after - with_minmax} materiales con min/max")

        # Muestra de materiales actualizados
        sample_after = Material.query.filter(
            (Material.min_stock > 0) | (Material.max_stock > 0)
        ).limit(10).all()
        print("\nMuestra de materiales con min/max actualizados:")
        for mat in sample_after:
            print(f"  - {mat.code}: {mat.name}")
            print(f"    Min: {mat.min_stock} | Max: {mat.max_stock}")

        # Estadísticas de min/max
        print("\n📊 ESTADÍSTICAS DE MIN/MAX:")
        print("-" * 70)

        stats = db.session.query(
            func.avg(Material.min_stock).label('avg_min'),
            func.avg(Material.max_stock).label('avg_max'),
            func.max(Material.min_stock).label('max_min'),
            func.max(Material.max_stock).label('max_max')
        ).filter(
            (Material.min_stock > 0) | (Material.max_stock > 0)
        ).first()

        if stats.avg_min:
            print(f"  Promedio mínimo: {stats.avg_min:.2f}")
            print(f"  Promedio máximo: {stats.avg_max:.2f}")
            print(f"  Mayor valor mínimo: {stats.max_min}")
            print(f"  Mayor valor máximo: {stats.max_max}")

        print("\n" + "="*70)
        print("✅ SINCRONIZACIÓN MIN/MAX COMPLETADA")
        print("="*70 + "\n")


if __name__ == '__main__':
    force_sync()
    sync_minmax()