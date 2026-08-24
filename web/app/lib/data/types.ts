export type searchJobInput2 = {
    title : string,
    location : string,
}

export type searchJobresult2 = {
    company : string,
    title : string,
    location : string,
    salary : number
}

export type serachResultObject2 = {
    structuredContent : {
            result : searchJobresult2[]
    }
}