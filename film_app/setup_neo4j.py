# film_app/setup_neo4j.py
from .neo4j_driver import get_session

def setup_neo4j_constraints():
    """
    Create necessary constraints and indexes in Neo4j
    """
    
    constraints = [
        # User constraints
        "CREATE CONSTRAINT user_uid_unique IF NOT EXISTS FOR (u:User) REQUIRE u.uid IS UNIQUE",
        "CREATE CONSTRAINT user_username_unique IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
        "CREATE CONSTRAINT user_email_unique IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
        
        # Movie constraints (if not already exists)
        "CREATE CONSTRAINT movie_id_unique IF NOT EXISTS FOR (m:Movie) REQUIRE m.id IS UNIQUE",
    ]
    
    try:
        with get_session() as session:
            for constraint in constraints:
                session.run(constraint)
                print(f"✓ Created constraint: {constraint}")
        
        print("\n✅ Neo4j constraints created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating constraints: {e}")

def create_first_admin():
    """
    Create the first admin user if no users exist
    """
    from .models import User
    
    # Check if any users exist
    users = User.nodes.all()
    
    if not users:
        # Create admin user
        admin = User(
            username='admin',
            email='admin@filmenneo.com',
            first_name='Admin',
            last_name='User',
            is_admin=True
        )
        admin.set_password('admin123')
        admin.save()
        
        print("✅ Created first admin user:")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   Email: admin@filmenneo.com")
        
        return admin
    else:
        print("ℹ️  Users already exist, skipping admin creation")
        return None

if __name__ == "__main__":
    # Run this from Django shell or management command
    setup_neo4j_constraints()
    create_first_admin()