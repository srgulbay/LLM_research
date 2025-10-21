class ExampleController {
    constructor(private exampleService: ExampleService) {}

    public async getExample(req: Request, res: Response): Promise<void> {
        try {
            const data = await this.exampleService.fetchExampleData();
            res.status(200).json(data);
        } catch (error) {
            res.status(500).json({ message: 'Error fetching example data' });
        }
    }

    public async createExample(req: Request, res: Response): Promise<void> {
        try {
            const newData = await this.exampleService.createExampleData(req.body);
            res.status(201).json(newData);
        } catch (error) {
            res.status(500).json({ message: 'Error creating example data' });
        }
    }
}

export default ExampleController;