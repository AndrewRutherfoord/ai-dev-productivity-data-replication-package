# import logging

# from driller.cloner import clone_repository
# from driller.drillers.driller import ConfigDriller
# from driller.util import load_yaml, parse_config

# from driller.driller_config import DrillConfig, apply_defaults

# logger = logging.getLogger(__name__)

# from unittest import TestCase

# class TestConfigDriller(TestCase):
#     def test_drill(self):
#         self.drill_repositories("tests/test_config.yaml")
        

#     def execute_drill_job(self, conf: DrillConfig):
#         project = conf.project
#         if project.url:
#             clone_repository(
#                 repository_url=project.url, repository_location=project.repo
#             )
#         logger.info(
#             f"Drilling {project.project_id} between {project.start_date} and {project.end_date}"
#         )
#         logger.debug(f"{ project.repo }")

#         # Instantiate instance of driller class
#         driller = ConfigDriller(conf.neo, project)

#         try:
#             driller.init_db()
#         except Exception as exc:
#             print("DB already initialized")

#         driller.drill_batch()
#         driller.merge_all()

#     def drill_repositories(self, file) -> list[DrillConfig]:
#         conf = load_yaml(file)
#         logger.warning(conf)
        
#         neo, defaults, projects = parse_config(conf)
        
#         assert neo is not None
#         assert defaults is not None
#         assert projects is not None
        
#         for project in projects:
#             p = apply_defaults(project, defaults=defaults)
#             config = DrillConfig(neo=neo, project=p)
#             logger.info(config)
#             self.execute_drill_job(config)    
