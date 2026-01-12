# film_app/management/commands/setup_database.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from film_app.neo4j_driver import test_connection

class Command(BaseCommand):
    help = 'Setup database and create admin user'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up database...'))
        
        # Test Neo4j connection
        self.stdout.write('Testing Neo4j connection...')
        result = test_connection()
        self.stdout.write(f'Neo4j: {result}')
        
        # Create admin user if not exists
        User = get_user_model()
        
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@filmenneo.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Created admin user: {admin.username}'))
            self.stdout.write(self.style.WARNING('   Username: admin'))
            self.stdout.write(self.style.WARNING('   Password: admin123'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Admin user already exists'))
        
        # Create constraints in Neo4j
        self.create_neo4j_constraints()
        
        self.stdout.write(self.style.SUCCESS('✅ Setup completed!'))
    
    def create_neo4j_constraints(self):
        """Create constraints in Neo4j"""
        from film_app.neo4j_driver import get_session
        
        constraints = [
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT user_username_unique IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
            "CREATE CONSTRAINT user_email_unique IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
        ]
        
        try:
            with get_session() as session:
                for constraint in constraints:
                    session.run(constraint)
                    self.stdout.write(f'✓ Created constraint: {constraint[:50]}...')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating constraints: {e}'))