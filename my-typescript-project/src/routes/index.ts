import { Router } from 'express';
import ExampleController from '../controllers/exampleController';
import ExampleService from '../services/exampleService';

const router = Router();
const exampleService = new ExampleService();
const exampleController = new ExampleController(exampleService);

router.get('/example', exampleController.getExample.bind(exampleController));
router.post('/example', exampleController.createExample.bind(exampleController));

export default router;