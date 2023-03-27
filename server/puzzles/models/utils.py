from django.db.models import Manager, Model


class SlugManager(Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class SlugModel(Model):
    objects = SlugManager()

    def natural_key(self):
        return (self.slug,)

    class Meta:
        abstract = True
