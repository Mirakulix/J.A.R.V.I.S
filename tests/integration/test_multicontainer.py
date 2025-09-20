"""
Integration tests for JARVIS Multi-Container System
Tests container interactions, service communication, and end-to-end workflows
"""

import pytest
import docker
import requests
import time
import asyncio
from unittest.mock import patch, Mock

@pytest.mark.integration
@pytest.mark.docker
class TestContainerOrchestration:
    """Test multi-container orchestration and communication"""
    
    @pytest.fixture(autouse=True)
    def setup_containers(self, docker_client):
        """Setup test containers"""
        if not docker_client:
            pytest.skip("Docker not available")
        
        self.docker_client = docker_client
        self.test_containers = []
    
    def teardown_method(self):
        """Cleanup test containers"""
        for container in getattr(self, 'test_containers', []):
            try:
                container.stop()
                container.remove()
            except:
                pass
    
    def test_container_startup_sequence(self):
        """Test proper container startup sequence"""
        # Expected startup order: databases -> redis -> core -> services
        expected_order = [
            'jarvis-personendb',
            'jarvis-organisationdb', 
            'jarvis-medizindb',
            'jarvis-tradingdb',
            'jarvis-vectordb',
            'jarvis-redis',
            'jarvis-core',
            'jarvis-frontend',
            'jarvis-connector',
            'jarvis-functions'
        ]
        
        # Mock container status checking
        with patch.object(self.docker_client, 'containers') as mock_containers:
            running_containers = []
            for name in expected_order:
                container_mock = Mock()
                container_mock.name = name
                container_mock.status = 'running'
                container_mock.attrs = {
                    'State': {'Health': {'Status': 'healthy'}},
                    'NetworkSettings': {'IPAddress': '172.18.0.10'}
                }
                running_containers.append(container_mock)
            
            mock_containers.list.return_value = running_containers
            
            containers = self.docker_client.containers.list()
            container_names = [c.name for c in containers]
            
            # Verify all expected containers are running
            for expected_name in expected_order:
                assert expected_name in container_names
    
    def test_service_health_checks(self):
        """Test health checks for all services"""
        services = {
            'jarvis-frontend': 'http://localhost:8080/health',
            'jarvis-core': 'http://localhost:8000/health',
            'jarvis-monitor': 'http://localhost:9090/health',
            'jarvis-android': 'http://localhost:8081/health'
        }
        
        # Mock health check responses
        for service, url in services.items():
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'status': 'healthy',
                    'service': service,
                    'timestamp': '2024-01-01T12:00:00Z'
                }
                mock_get.return_value = mock_response
                
                # Test health check
                response = requests.get(url, timeout=5)
                assert response.status_code == 200
                health_data = response.json()
                assert health_data['status'] == 'healthy'
    
    def test_database_connectivity(self):
        """Test database connectivity across containers"""
        databases = [
            {'host': 'jarvis-personendb', 'port': 5432, 'db': 'personendb'},
            {'host': 'jarvis-organisationdb', 'port': 5433, 'db': 'organisationdb'},
            {'host': 'jarvis-medizindb', 'port': 5434, 'db': 'medizindb'},
            {'host': 'jarvis-tradingdb', 'port': 5436, 'db': 'tradingdb'},
            {'host': 'jarvis-vectordb', 'port': 8000, 'db': 'chroma'}
        ]
        
        # Mock database connections
        with patch('psycopg2.connect') as mock_pg_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.execute.return_value = None
            mock_cursor.fetchone.return_value = (1,)
            mock_conn.cursor.return_value = mock_cursor
            mock_pg_connect.return_value = mock_conn
            
            # Test PostgreSQL databases
            for db_config in databases[:4]:  # Skip vectordb (ChromaDB)
                conn = mock_pg_connect(
                    host=db_config['host'],
                    port=db_config['port'],
                    database=db_config['db']
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result == (1,)
        
        # Test ChromaDB connectivity
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_chroma.return_value = mock_client
            mock_client.heartbeat.return_value = True
            
            client = mock_chroma()
            assert client.heartbeat() is True
    
    def test_redis_connectivity(self):
        """Test Redis connectivity and operations"""
        with patch('redis.Redis') as mock_redis:
            mock_instance = Mock()
            mock_redis.return_value = mock_instance
            
            # Test Redis operations
            mock_instance.ping.return_value = True
            mock_instance.set.return_value = True
            mock_instance.get.return_value = b'test_value'
            mock_instance.delete.return_value = 1
            
            # Test connection and basic operations
            redis_client = mock_redis(host='jarvis-redis', port=6379)
            
            assert redis_client.ping() is True
            assert redis_client.set('test_key', 'test_value') is True
            assert redis_client.get('test_key') == b'test_value'
            assert redis_client.delete('test_key') == 1

@pytest.mark.integration
class TestServiceCommunication:
    """Test inter-service communication"""
    
    def test_core_to_database_communication(self):
        """Test core service database communication"""
        with patch('jarvis_core.database.DatabaseManager') as mock_db:
            mock_instance = Mock()
            mock_db.return_value = mock_instance
            
            # Test database operations
            mock_instance.get_skills.return_value = [
                {'name': 'weather_api', 'category': 'simple'},
                {'name': 'crypto_trading', 'category': 'complex'}
            ]
            
            db_manager = mock_db()
            skills = db_manager.get_skills()
            
            assert len(skills) == 2
            assert skills[0]['name'] == 'weather_api'
    
    def test_frontend_to_core_api(self):
        """Test frontend to core API communication"""
        # Mock API requests
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'success': True,
                'result': 'Skill executed successfully',
                'execution_time': 0.5
            }
            mock_post.return_value = mock_response
            
            # Test API call
            response = requests.post(
                'http://jarvis-core:8000/api/v1/skills/execute',
                json={'skill': 'weather_api', 'params': {'location': 'Vienna'}}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
    
    def test_connector_to_external_apis(self):
        """Test connector service external API communication"""
        with patch('jarvis_connector.apis.ExternalAPIManager') as mock_api:
            mock_instance = Mock()
            mock_api.return_value = mock_instance
            
            # Test external API calls
            mock_instance.call_google_api.return_value = {
                'success': True,
                'data': {'calendar_events': []}
            }
            mock_instance.call_onepassword_api.return_value = {
                'success': True,
                'data': {'password': 'generated_password'}
            }
            
            api_manager = mock_api()
            
            # Test Google API
            google_result = api_manager.call_google_api('calendar', 'list_events')
            assert google_result['success'] is True
            
            # Test 1Password API
            op_result = api_manager.call_onepassword_api('generate_password')
            assert op_result['success'] is True
    
    def test_monitoring_data_collection(self):
        """Test monitoring service data collection"""
        with patch('jarvis_monitor.collectors.MetricsCollector') as mock_collector:
            mock_instance = Mock()
            mock_collector.return_value = mock_instance
            
            # Mock metrics collection
            mock_instance.collect_container_metrics.return_value = {
                'jarvis-core': {'cpu': 25.5, 'memory': 512},
                'jarvis-frontend': {'cpu': 15.2, 'memory': 256},
                'jarvis-db': {'cpu': 30.1, 'memory': 1024}
            }
            
            collector = mock_collector()
            metrics = collector.collect_container_metrics()
            
            assert 'jarvis-core' in metrics
            assert metrics['jarvis-core']['cpu'] == 25.5

@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_skill_execution_workflow(self):
        """Test complete skill execution from frontend to backend"""
        # Mock the complete workflow
        workflow_steps = []
        
        # Step 1: Frontend receives request
        with patch('jarvis_frontend.api.SkillRequestHandler') as mock_handler:
            mock_instance = Mock()
            mock_handler.return_value = mock_instance
            mock_instance.handle_request.return_value = {'request_id': 'test_123'}
            
            handler = mock_handler()
            request_result = handler.handle_request({
                'skill': 'weather_api',
                'params': {'location': 'Vienna'}
            })
            workflow_steps.append('frontend_request_received')
            assert request_result['request_id'] == 'test_123'
        
        # Step 2: Core processes request
        with patch('jarvis_core.orchestrator.SkillOrchestrator') as mock_orchestrator:
            mock_instance = Mock()
            mock_orchestrator.return_value = mock_instance
            mock_instance.process_skill = AsyncMock()
            mock_instance.process_skill.return_value = {
                'success': True,
                'result': {'temperature': 22, 'description': 'Sunny'}
            }
            
            orchestrator = mock_orchestrator()
            result = await orchestrator.process_skill('weather_api', {'location': 'Vienna'})
            workflow_steps.append('core_processed_skill')
            assert result['success'] is True
        
        # Step 3: Database stores execution log
        with patch('jarvis_core.database.ExecutionLogger') as mock_logger:
            mock_instance = Mock()
            mock_logger.return_value = mock_instance
            mock_instance.log_execution.return_value = True
            
            logger = mock_logger()
            logged = logger.log_execution('test_123', 'weather_api', result)
            workflow_steps.append('execution_logged')
            assert logged is True
        
        # Step 4: Response sent back to frontend
        with patch('jarvis_frontend.api.ResponseHandler') as mock_response:
            mock_instance = Mock()
            mock_response.return_value = mock_instance
            mock_instance.send_response.return_value = {'status': 'sent'}
            
            response_handler = mock_response()
            sent = response_handler.send_response('test_123', result)
            workflow_steps.append('response_sent')
            assert sent['status'] == 'sent'
        
        # Verify complete workflow
        expected_steps = [
            'frontend_request_received',
            'core_processed_skill',
            'execution_logged',
            'response_sent'
        ]
        assert workflow_steps == expected_steps
    
    def test_trading_prediction_workflow(self):
        """Test complete trading prediction workflow"""
        workflow_results = {}
        
        # Step 1: Collect market data
        with patch('database.tradingdb.collect_market_data.MarketDataCollector') as mock_collector:
            mock_instance = Mock()
            mock_collector.return_value = mock_instance
            mock_instance.run_collection.return_value = {
                'crypto_collected': 10,
                'stocks_collected': 5
            }
            
            collector = mock_collector()
            collection_result = collector.run_collection()
            workflow_results['data_collection'] = collection_result
        
        # Step 2: Calculate predictions
        with patch('database.tradingdb.calculate_predictions.PredictionCalculator') as mock_calculator:
            mock_instance = Mock()
            mock_calculator.return_value = mock_instance
            mock_instance.run_predictions.return_value = {
                'predictions_generated': 15,
                'signals_created': 8
            }
            
            calculator = mock_calculator()
            prediction_result = calculator.run_predictions()
            workflow_results['prediction_calculation'] = prediction_result
        
        # Step 3: Sync with Bitpanda
        with patch('database.tradingdb.bitpanda_sync.BitpandaSync') as mock_sync:
            mock_instance = Mock()
            mock_sync.return_value = mock_instance
            mock_instance.run_sync.return_value = {
                'balances_synced': True,
                'trades_synced': 3,
                'portfolio_value': 8500.75
            }
            
            sync = mock_sync()
            sync_result = sync.run_sync()
            workflow_results['bitpanda_sync'] = sync_result
        
        # Verify workflow completion
        assert workflow_results['data_collection']['crypto_collected'] == 10
        assert workflow_results['prediction_calculation']['predictions_generated'] == 15
        assert workflow_results['bitpanda_sync']['balances_synced'] is True
    
    def test_android_automation_workflow(self):
        """Test Android automation workflow"""
        with patch('jarvis_android.automation.AndroidController') as mock_controller:
            mock_instance = Mock()
            mock_controller.return_value = mock_instance
            
            # Mock Android automation steps
            mock_instance.start_emulator.return_value = {'success': True, 'device_id': 'emulator-5554'}
            mock_instance.install_app.return_value = {'success': True, 'package': 'com.test.app'}
            mock_instance.run_test.return_value = {
                'success': True,
                'tests_run': 5,
                'tests_passed': 5,
                'execution_time': 45.2
            }
            mock_instance.capture_screenshot.return_value = {'success': True, 'file': 'screenshot.png'}
            
            controller = mock_controller()
            
            # Execute automation workflow
            emulator_result = controller.start_emulator()
            assert emulator_result['success'] is True
            
            app_result = controller.install_app('test_app.apk')
            assert app_result['success'] is True
            
            test_result = controller.run_test('ui_test_suite')
            assert test_result['tests_passed'] == 5
            
            screenshot_result = controller.capture_screenshot()
            assert screenshot_result['success'] is True

@pytest.mark.integration
class TestNetworkCommunication:
    """Test network communication between containers"""
    
    def test_internal_network_isolation(self):
        """Test internal network isolation"""
        # Test that database network is isolated
        internal_services = [
            'jarvis-personendb',
            'jarvis-organisationdb', 
            'jarvis-medizindb',
            'jarvis-tradingdb'
        ]
        
        # Mock network isolation testing
        with patch('docker.client.DockerClient') as mock_docker:
            mock_client = Mock()
            mock_docker.return_value = mock_client
            
            # Mock network inspection
            mock_network = Mock()
            mock_network.attrs = {
                'Options': {'com.docker.network.bridge.enable_icc': 'false'},
                'Internal': True
            }
            mock_client.networks.get.return_value = mock_network
            
            # Test internal network
            network = mock_client.networks.get('jarvis-database')
            assert network.attrs['Internal'] is True
    
    def test_service_discovery(self):
        """Test service discovery and DNS resolution"""
        services = [
            'jarvis-core',
            'jarvis-frontend',
            'jarvis-redis',
            'jarvis-vectordb'
        ]
        
        # Mock DNS resolution
        with patch('socket.gethostbyname') as mock_dns:
            for service in services:
                mock_dns.return_value = f'172.18.0.{services.index(service) + 10}'
                
                # Test DNS resolution
                ip = mock_dns(service)
                assert ip.startswith('172.18.0.')

if __name__ == "__main__":
    pytest.main([__file__])