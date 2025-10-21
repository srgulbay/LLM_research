// This file defines custom types and interfaces used throughout the application. 

// Example of a custom type
export type User = {
    id: string;
    name: string;
    email: string;
};

// Example of an interface
export interface ExampleServiceInterface {
    getData(id: string): Promise<User>;
    saveData(user: User): Promise<void>;
}