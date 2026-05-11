"""
Test Data Creation Script for CyberShield
Run this in Django shell: python manage.py shell < create_test_data.py
"""

from django.contrib.auth.models import User
from users.models import UserProfile, Role
from teams.models import Team, TeamMember

print("Creating test data...")

# Create Admin User
admin, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@cybershield.com',
        'is_staff': True,
        'is_superuser': True
    }
)
if created:
    admin.set_password('admin123')
    admin.save()
    admin.profile.role = Role.ADMIN
    admin.profile.save()
    print(f"✓ Created admin user: {admin.username}")
else:
    print(f"✓ Admin user already exists: {admin.username}")

# Create Pentesters
pentesters = [
    {'username': 'john_web', 'email': 'john@cybershield.com', 'role': Role.WEB_PENTESTER, 'first_name': 'John', 'last_name': 'Doe'},
    {'username': 'sarah_mobile', 'email': 'sarah@cybershield.com', 'role': Role.MOBILE_PENTESTER, 'first_name': 'Sarah', 'last_name': 'Smith'},
    {'username': 'mike_web', 'email': 'mike@cybershield.com', 'role': Role.WEB_PENTESTER, 'first_name': 'Mike', 'last_name': 'Johnson'},
]

created_pentesters = []
for data in pentesters:
    user, created = User.objects.get_or_create(
        username=data['username'],
        defaults={
            'email': data['email'],
            'first_name': data['first_name'],
            'last_name': data['last_name']
        }
    )
    if created:
        user.set_password('pass123')
        user.save()
        user.profile.role = data['role']
        user.profile.save()
        print(f"✓ Created pentester: {user.username} ({data['role']})")
    else:
        print(f"✓ Pentester already exists: {user.username}")
    created_pentesters.append(user)

# Create Analysts
analysts = [
    {'username': 'alex_network', 'email': 'alex@cybershield.com', 'role': Role.NETWORK_ANALYST, 'first_name': 'Alex', 'last_name': 'Brown'},
    {'username': 'emma_soc', 'email': 'emma@cybershield.com', 'role': Role.SOC_ANALYST, 'first_name': 'Emma', 'last_name': 'Wilson'},
    {'username': 'david_network', 'email': 'david@cybershield.com', 'role': Role.NETWORK_ANALYST, 'first_name': 'David', 'last_name': 'Lee'},
]

created_analysts = []
for data in analysts:
    user, created = User.objects.get_or_create(
        username=data['username'],
        defaults={
            'email': data['email'],
            'first_name': data['first_name'],
            'last_name': data['last_name']
        }
    )
    if created:
        user.set_password('pass123')
        user.save()
        user.profile.role = data['role']
        user.profile.save()
        print(f"✓ Created analyst: {user.username} ({data['role']})")
    else:
        print(f"✓ Analyst already exists: {user.username}")
    created_analysts.append(user)

# Create Clients
clients = [
    {'username': 'client1', 'email': 'client1@example.com', 'role': Role.CLIENT, 'first_name': 'Client', 'last_name': 'One'},
    {'username': 'client2', 'email': 'client2@example.com', 'role': Role.CLIENT, 'first_name': 'Client', 'last_name': 'Two'},
]

created_clients = []
for data in clients:
    user, created = User.objects.get_or_create(
        username=data['username'],
        defaults={
            'email': data['email'],
            'first_name': data['first_name'],
            'last_name': data['last_name']
        }
    )
    if created:
        user.set_password('pass123')
        user.save()
        user.profile.role = data['role']
        user.profile.save()
        print(f"✓ Created client: {user.username}")
    else:
        print(f"✓ Client already exists: {user.username}")
    created_clients.append(user)

# Create Teams
teams_data = [
    {
        'name': 'Red Team',
        'description': 'Offensive security team specializing in penetration testing and vulnerability assessment',
        'team_lead': created_pentesters[0],  # john_web
        'members': [created_pentesters[0], created_pentesters[2], created_analysts[0]]  # John, Mike, Alex
    },
    {
        'name': 'SOC Team',
        'description': 'Security Operations Center - monitoring and incident response',
        'team_lead': created_analysts[1],  # emma_soc
        'members': [created_analysts[1], created_analysts[2]]  # Emma, David
    },
    {
        'name': 'Mobile Security Team',
        'description': 'Specialized team for mobile application security testing',
        'team_lead': created_pentesters[1],  # sarah_mobile
        'members': [created_pentesters[1], created_analysts[0]]  # Sarah, Alex
    },
]

print("\nCreating teams...")
for team_data in teams_data:
    team, created = Team.objects.get_or_create(
        name=team_data['name'],
        defaults={
            'description': team_data['description'],
            'team_lead': team_data['team_lead']
        }
    )

    if created:
        print(f"✓ Created team: {team.name}")

        # Add members
        for member_user in team_data['members']:
            TeamMember.objects.get_or_create(
                team=team,
                user=member_user
            )
            print(f"  → Added {member_user.username} to {team.name}")
    else:
        print(f"✓ Team already exists: {team.name}")

print("\n" + "="*50)
print("TEST DATA CREATION COMPLETE!")
print("="*50)
print("\n📋 Summary:")
print(f"Total Users: {User.objects.count()}")
print(f"Total Teams: {Team.objects.count()}")
print(f"Pentesters: {User.objects.filter(profile__role__contains='pentester').count()}")
print(f"Analysts: {User.objects.filter(profile__role__contains='analyst').count()}")
print(f"Clients: {User.objects.filter(profile__role=Role.CLIENT).count()}")

print("\n🔐 Login Credentials:")
print("="*50)
print("Admin:")
print("  Username: admin")
print("  Password: admin123")
print("  URL: http://127.0.0.1:8000/staff/login/")
print("\nPentesters/Analysts:")
print("  Password for all: pass123")
print("  Usernames: john_web, sarah_mobile, mike_web, alex_network, emma_soc, david_network")
print("\n✅ You can now login and test team management!")