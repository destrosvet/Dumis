from ..factories import PreferencesFactory, CompanyFactory, AdvertTypeFactory


class PreferencesDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.company = CompanyFactory(name="Testing company", internet_domain="www.test.cz")

        cls.advert_types = [
            AdvertTypeFactory(description="Koupím"),
            AdvertTypeFactory(description="Prodám"),
            AdvertTypeFactory(description="Ostatní"),
        ]

        cls.p_fault_notif = PreferencesFactory(
            key="mail.template.fault.notification", value="Uživatel {author} vložil novou závadu {link}: <br><br><br>{description}"
        )
        cls.p_fault_assigned = PreferencesFactory(
            key="mail.template.fault.assigned", value="Uživatel {assignor} vám přiřadil tiket {link}: <br><br><br>{description}"
        )
        cls.p_fault_closed = PreferencesFactory(
            key="mail.template.fault.closed", value="Uživatel {user} uzavřel tiket {link}: <br><br><br>{description}"
        )
        cls.p_fault_reopened = PreferencesFactory(
            key="mail.template.fault.reopened", value="Uživatel {user} znovu otevřel tiket {link}: <br><br><br>{description}"
        )
        cls.p_project_notif = PreferencesFactory(
            key="mail.template.project.notification",
            value="Uživatel {author} založil nový projekt {link}: <br><br><br>{description}",
        )
        cls.p_project_comment_notif = PreferencesFactory(
            key="mail.template.project.comment.notification",
            value="Uživatel {author} přidal nový komentář k projektu {link}: <br><br><br>{comment}",
        )
        cls.p_project_assigned = PreferencesFactory(
            key="mail.template.project.assigned",
            value="Uživatel {assignor} vám přiřadil projekt {link}: <br><br><br>{description}",
        )
        cls.p_project_status_changed = PreferencesFactory(
            key="mail.template.project.status.changed",
            value='Uživatel {user} změnil stav projektu {link} z "{old_status}" na "{new_status}".',
        )
