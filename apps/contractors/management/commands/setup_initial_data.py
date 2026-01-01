from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.contractors.models import Category, Skill


class Command(BaseCommand):
    help = 'Set up initial data for the application'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up initial data...'))
        
        # Load categories and skills
        try:
            call_command('loaddata', 'fixtures/categories.json')
            self.stdout.write(self.style.SUCCESS('✅ Categories loaded successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error loading categories: {e}'))
        
        try:
            call_command('loaddata', 'fixtures/skills.json')
            self.stdout.write(self.style.SUCCESS('✅ Skills loaded successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error loading skills: {e}'))
        
        # Display summary
        categories_count = Category.objects.count()
        skills_count = Skill.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Summary:'))
        self.stdout.write(f'   Categories: {categories_count}')
        self.stdout.write(f'   Skills: {skills_count}')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Initial data setup completed!'))
        self.stdout.write('Next steps:')
        self.stdout.write('1. Create a superuser: python manage.py createsuperuser')
        self.stdout.write('2. Start the development server: python manage.py runserver')
        self.stdout.write('3. Visit http://localhost:8000/api/docs/ for API documentation')