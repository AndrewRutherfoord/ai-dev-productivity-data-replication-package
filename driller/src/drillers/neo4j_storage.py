import logging

from neo4j import GraphDatabase
from neo4j.exceptions import TransientError, ClientError

logger = logging.getLogger(__name__)


class Neo4jStorage:
    """Provides groundwork for performing queries against a Neo4j Database. Intended to be extended."""

    def __init__(
        self,
        user: str = "neo4j",
        password: str = "",
        host: str = "neo4j",
        port: int = 7687,
        batch_size: int = 200,
    ):
        uri = f"bolt://{host}:{port}"
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.batch_size = batch_size
        self.batch = []

    def connect(self):
        """
        Validates connectivity to Neo4j.
        """
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
        except Exception as e:
            logger.exception("Failed to connect to Neo4j")
            raise e

    def close(self):
        """
        Closes the Neo4j connection.
        Processes remaining batch just before close.
        """
        self._process_batch()
        self.driver.close()

    def _add_to_batch(self, query, parameters):
        """Adds a query to the batch of queries.

        Args:
            query (str): query string
            parameters (dict): the parameters that will be inserted into the queries.
        """
        self.batch.append((query, parameters))
        if len(self.batch) >= self.batch_size:
            self._process_batch()

    def _run_query(self, query, params):
        try:
            with self.driver.session() as session:
                session.run(query, params)
        except ClientError as e:
            logger.error(f"Query failed '{query}' with args ({params}) ")
            logger.exception(e)

    def _process_batch(self):
        """Runs a batch of cypher commands as a transaciton on the Neo4j DB.
        In testing with multiple workers it would occasianlly enounter a `TransientError` causes by a deadlock on Neo4j.
        If Deadlock enountered it will try to re-run the transaction. If fails 3 times, throws the error.
        """
        try_again = 3
        while try_again > 0:
            logger.debug("Processing Batch")
            try:
                if self.batch:
                    with self.driver.session() as session:
                        with session.begin_transaction() as tx:
                            for operation in self.batch:
                                tx.run(*operation)
                    self.batch = []
                return
            except TransientError as e:
                logger.exception("Encountered a TransientError", e)
                try_again -= 1
                if try_again == 0:
                    raise e
            except Exception as e:
                logger.exception(e)
                raise e
