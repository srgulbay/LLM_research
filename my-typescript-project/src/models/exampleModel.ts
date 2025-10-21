class ExampleModel {
    constructor(public id: number, public name: string, public description: string) {}

    validate(): boolean {
        if (!this.name || this.name.length < 3) {
            throw new Error("Name must be at least 3 characters long.");
        }
        if (!this.description || this.description.length < 10) {
            throw new Error("Description must be at least 10 characters long.");
        }
        return true;
    }
}

export default ExampleModel;